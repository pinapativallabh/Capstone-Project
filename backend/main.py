from fastapi import FastAPI, UploadFile, File, Body
from pydantic import BaseModel
import fitz
import ollama
import re
import json
import os
import uuid
import json
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_store import get_collection
from db import init_db, save_result, get_student_stats
from db import get_wrong_questions
from db import get_all_students, get_student_summary
from db import get_recent_wrong_questions
from db import get_wrong_summary

init_db()

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------- Request Models -----------
class QuestionRequest(BaseModel):
    file_id: str
    question: str

class AdaptiveQuizRequest(BaseModel):
    student_id: str
    file_id: str
    num_questions: int = 5


# ----------- Routes -----------
@app.get("/")
def root():
    return {"status": "Backend running"}


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return {"error": "Only PDF files allowed"}

    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}.pdf")

    # Save PDF
    with open(save_path, "wb") as f:
        f.write(await file.read())

    # Extract text
    doc = fitz.open(save_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # Chunk text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100
    )
    chunks = splitter.split_text(full_text)

    # Store in ChromaDB
    collection = get_collection()

    ids = [f"{file_id}_{i}" for i in range(len(chunks))]
    metadatas = [{"file_id": file_id, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        ids=ids,
        metadatas=metadatas
    )

    return {
        "message": "PDF uploaded + stored in vector DB",
        "file_id": file_id,
        "chunks_stored": len(chunks)
    }


@app.post("/ask/")
async def ask_question(
    file_id: str = Body(...),
    question: str = Body(...)
):
    collection = get_collection()

    results = collection.query(
        query_texts=[question],
        n_results=25,
        where={"file_id": file_id}
    )

    retrieved_docs = results["documents"][0]
    retrieved_meta = results["metadatas"][0]

    if not retrieved_docs:
        return {
            "file_id": file_id,
            "question": question,
            "answer": "Not found in the provided material.",
            "chunks_used": []
        }

    context_blocks = []
    for i, doc in enumerate(retrieved_docs):
        context_blocks.append(f"[Chunk {i+1}] {doc}")

    context = "\n\n".join(context_blocks)

    retrieved_docs = retrieved_docs[:10]
    retrieved_meta = retrieved_meta[:10]
    prompt = f"""
You are a faculty-material grounded learning assistant.

You MUST answer using ONLY the context below.

If the answer exists anywhere in the context, you MUST answer it.
Only if the answer is completely absent, reply exactly:
Not found in the provided material.

Context:
{context}

Question:
{question}

Give a direct answer in 1-5 lines, then mention chunks used like:
(Used: Chunk 2)

Answer:
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
    "answer": response["message"]["content"]
    }

class SummaryRequest(BaseModel):
    file_id: str


@app.post("/summarize/")
async def summarize_pdf(req: SummaryRequest):
    collection = get_collection()

    # Get ALL chunks for that PDF
    data = collection.get(where={"file_id": req.file_id})

    docs = data["documents"]

    if not docs:
        return {"error": "No content found for this file_id"}

    # Join limited chunks (avoid huge prompt)
    combined_text = "\n\n".join(docs[:30])  # you can increase later

    prompt = f"""
You are a study assistant.

Summarize the following faculty material into:
1. Short summary (5-7 lines)
2. Key topics covered (bullet points)
3. Important terms (bullet list)

Material:
{combined_text}
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "file_id": req.file_id,
        "summary": response["message"]["content"]
    }
class QuizRequest(BaseModel):
    file_id: str
    num_questions: int = 5


@app.post("/generate-quiz/")
async def generate_quiz(req: QuizRequest):
    collection = get_collection()

    data = collection.get(where={"file_id": req.file_id})
    docs = data["documents"]

    if not docs:
        return {"error": "No content found for this file_id"}

    combined_text = "\n\n".join(docs[:25])

    prompt = f"""
You are a quiz generator.

Create {req.num_questions} multiple-choice questions (MCQs) strictly from the given material.

Rules:
- Each question must have 4 options (A, B, C, D)
- Provide correct answer key
- Provide 1-line explanation
- Do NOT use outside knowledge
- Output must be valid JSON only (no extra text)

Format:
[
  {{
    "question": "...",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "answer": "A",
    "explanation": "..."
  }}
]

Material:
{combined_text}
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response["message"]["content"]

    # Extract the first JSON array [...]
    match = re.search(r'\[[\s\S]*\]', raw)

    if not match:
        return {"file_id": req.file_id, "quiz": [], "raw_output": raw}

    json_text = match.group(0)

    try:
        quiz_list = json.loads(json_text)
    except:
        quiz_list = []

    return {
        "file_id": req.file_id,
        "quiz": quiz_list
    }
class SubmitQuizRequest(BaseModel):
    student_id: str
    file_id: str
    responses: list  # [{"question": "...", "selected": "A", "correct": "B"}]


@app.post("/submit-quiz/")
async def submit_quiz(req: SubmitQuizRequest):
    correct_count = 0

    for r in req.responses:
        question = r["question"]
        selected = r["selected"]
        correct = r["correct"]

        is_correct = 1 if selected == correct else 0
        if is_correct:
            correct_count += 1

        save_result(
            student_id=req.student_id,
            file_id=req.file_id,
            question=question,
            selected_option=selected,
            correct_option=correct,
            is_correct=is_correct
        )

    total = len(req.responses)

    return {
        "student_id": req.student_id,
        "file_id": req.file_id,
        "score": f"{correct_count}/{total}",
        "percentage": (correct_count / total) * 100
    }
class ProgressRequest(BaseModel):
    student_id: str
    file_id: str


@app.post("/student-progress/")
async def student_progress(req: ProgressRequest):
    total, correct = get_student_stats(req.student_id, req.file_id)
    wrongs = get_wrong_summary(req.student_id, req.file_id)


    accuracy = (correct / total) * 100 if total > 0 else 0

    wrong_list = []
    for w in wrongs:
        wrong_list.append({
            "question": w[0],
            "times_wrong": w[1]
    })


    # Generate roadmap using Ollama
    wrong_questions_text = "\n".join([f"- {w[0]}" for w in wrongs])

    prompt = f"""
You are a personalized learning assistant.

A student attempted a quiz from faculty material and got these questions wrong:
{wrong_questions_text}

Generate:
1. Weak topics inferred (bullet list)
2. What to revise (bullet list)
3. 5-step study roadmap (short)

Keep it simple and student-friendly.
"""

    roadmap = "No wrong answers yet."
    if len(wrongs) > 0:
        response = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}]
        )
        roadmap = response["message"]["content"]

    return {
        "student_id": req.student_id,
        "file_id": req.file_id,
        "total_attempted": total,
        "correct": correct,
        "accuracy": accuracy,
        "wrong_questions": wrong_list,
        "personalized_roadmap": roadmap
    }
class TeacherDashboardRequest(BaseModel):
    file_id: str


@app.post("/teacher-dashboard/")
async def teacher_dashboard(req: TeacherDashboardRequest):
    students = get_all_students(req.file_id)

    report = []
    for s in students:
        total, correct, accuracy = get_student_summary(s, req.file_id)
        report.append({
            "student_id": s,
            "attempted": total,
            "correct": correct,
            "accuracy": accuracy
        })

    return {
        "file_id": req.file_id,
        "student_report": report
    }
@app.post("/generate-adaptive-quiz/")
async def generate_adaptive_quiz(req: AdaptiveQuizRequest):
    collection = get_collection()

    data = collection.get(where={"file_id": req.file_id})
    docs = data["documents"]

    if not docs:
        return {"error": "No content found for this file_id"}

    combined_text = "\n\n".join(docs[:30])

    wrong_qs = get_recent_wrong_questions(req.student_id, req.file_id, limit=5)

    wrong_text = "\n".join([f"- {q}" for q in wrong_qs])

    prompt = f"""
You are an adaptive quiz generator.

A student previously got these questions wrong:
{wrong_text if wrong_qs else "No previous wrong questions."}

Task:
Generate {req.num_questions} new MCQs focused on the student's weak areas.

Rules:
- Questions must be strictly based on the given material.
- 4 options (A,B,C,D)
- Give correct answer + 1-line explanation
- Output ONLY valid JSON array (no extra text)

Format:
[
  {{
    "question": "...",
    "options": {{
      "A": "...",
      "B": "...",
      "C": "...",
      "D": "..."
    }},
    "answer": "A",
    "explanation": "..."
  }}
]

Material:
{combined_text}
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response["message"]["content"]

    match = re.search(r'\[[\s\S]*\]', raw)

    if not match:
        return {"file_id": req.file_id, "quiz": [], "raw_output": raw}

    json_text = match.group(0)

    try:
        quiz_list = json.loads(json_text)
    except:
        quiz_list = []

    return {
        "student_id": req.student_id,
        "file_id": req.file_id,
        "quiz": quiz_list
    }
