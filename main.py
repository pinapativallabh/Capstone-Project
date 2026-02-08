from fastapi import FastAPI, UploadFile, File, Body
from pydantic import BaseModel
import fitz
import ollama
import os
import uuid
import json
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_store import get_collection

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------- Request Models -----------
class QuestionRequest(BaseModel):
    file_id: str
    question: str


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

Give a direct answer in 1-3 lines, then mention chunks used like:
(Used: Chunk 2)

Answer:
"""

    response = ollama.chat(
        model="llama3:8b",
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "file_id": file_id,
        "question": question,
        "answer": response["message"]["content"],
        "chunks_used": [
            {"chunk_no": i+1, "metadata": retrieved_meta[i], "text": retrieved_docs[i]}
            for i in range(len(retrieved_docs))
        ]
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
