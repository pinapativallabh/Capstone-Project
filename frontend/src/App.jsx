import { useState } from "react";
import axios from "axios";

const API = "http://127.0.0.1:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState("upload");
  const [messages, setMessages] = useState([]);
  const [file, setFile] = useState(null);
  const [fileId, setFileId] = useState("");
  const [uploadResult, setUploadResult] = useState(null);

  const [question, setQuestion] = useState("");
  const [chatResult, setChatResult] = useState(null);

  const [summaryResult, setSummaryResult] = useState(null);

  const [quizCount, setQuizCount] = useState(5);
  const [quizResult, setQuizResult] = useState(null);

  const [studentId, setStudentId] = useState("student_1");
  const [quizAnswers, setQuizAnswers] = useState({});
  const [submitResult, setSubmitResult] = useState(null);

  const [progressResult, setProgressResult] = useState(null);

  const [teacherResult, setTeacherResult] = useState(null);

  // ---------------- Upload PDF ----------------
  const handleUpload = async () => {
    if (!file) return alert("Select a PDF first");

    const formData = new FormData();
    formData.append("file", file);

    const res = await axios.post(`${API}/upload-pdf/`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });

    setUploadResult(res.data);
    setFileId(res.data.file_id);
  };

  // ---------------- Ask Question ----------------
  const handleAsk = async () => {
  if (!fileId) return alert("Enter file_id first");
  if (!question) return alert("Enter question");

  const userMsg = { role: "user", text: question };
  setMessages((prev) => [...prev, userMsg]);

  const res = await axios.post(`${API}/ask/`, {
    file_id: fileId,
    question: question,
  });

  const botMsg = { role: "assistant", text: res.data.answer };
  setMessages((prev) => [...prev, botMsg]);

  setQuestion("");
};


  // ---------------- Summarize ----------------
  const handleSummarize = async () => {
    if (!fileId) return alert("Enter file_id first");

    const res = await axios.post(`${API}/summarize/`, {
      file_id: fileId,
    });

    setSummaryResult(res.data);
  };

  // ---------------- Generate Quiz ----------------
  const handleGenerateQuiz = async () => {
    if (!fileId) return alert("Enter file_id first");

    const res = await axios.post(`${API}/generate-quiz/`, {
      file_id: fileId,
      num_questions: quizCount,
    });
    console.log(res.data);
    console.log("QUIZ RESPONSE:", res.data);
  console.log("QUIZ:", res.data.quiz);

    setQuizResult(res.data.quiz);
    setQuizAnswers({});
    setSubmitResult(null);
  };

  const handleGenerateAdaptiveQuiz = async () => {
  if (!fileId) return alert("Enter file_id first");

  const res = await axios.post(`${API}/generate-adaptive-quiz/`, {
    student_id: studentId,
    file_id: fileId,
    num_questions: quizCount,
  });

  setQuizResult(res.data.quiz);
  setQuizAnswers({});
  setSubmitResult(null);
};

  // ---------------- Submit Quiz ----------------
  const handleSubmitQuiz = async () => {
    if (!quizResult) return alert("Generate quiz first");

    const responses = quizResult.map((q) => ({
      question: q.question,
      selected: quizAnswers[q.question] || "",
      correct: q.answer,
    }));

    const res = await axios.post(`${API}/submit-quiz/`, {
      student_id: studentId,
      file_id: fileId,
      responses: responses,
    });

    setSubmitResult(res.data);
  };

  // ---------------- Progress ----------------
  const handleProgress = async () => {
    const res = await axios.post(`${API}/student-progress/`, {
      student_id: studentId,
      file_id: fileId,
    });

    setProgressResult(res.data);
  };

  // ---------------- Teacher Dashboard ----------------
  const handleTeacherDashboard = async () => {
    const res = await axios.post(`${API}/teacher-dashboard/`, {
      file_id: fileId,
    });

    setTeacherResult(res.data);
  };

  // ---------------- UI ----------------
  return (
    <div style={{ fontFamily: "Arial", padding: "20px" }}>
      <h2>LLM Personalized Learning Assistant</h2>

      <div style={{ marginBottom: "15px" }}>
        <button onClick={() => setActiveTab("upload")}>Faculty Upload</button>{" "}
        <button onClick={() => setActiveTab("chat")}>Student Chat</button>{" "}
        <button onClick={() => setActiveTab("summary")}>Summary</button>{" "}
        <button onClick={() => setActiveTab("quiz")}>Quiz</button>{" "}
        <button onClick={() => setActiveTab("progress")}>Progress</button>{" "}
        <button onClick={() => setActiveTab("teacher")}>Teacher Dashboard</button>
      </div>

      <div style={{ marginBottom: "10px" }}>
        <label>File ID: </label>
        <input
          value={fileId}
          onChange={(e) => setFileId(e.target.value)}
          style={{ width: "400px" }}
        />
      </div>

      {/* Upload */}
      {activeTab === "upload" && (
        <div>
          <h3>Faculty PDF Upload</h3>
          <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
          <br /><br />
          <button onClick={handleUpload}>Upload PDF</button>

          {uploadResult && (
  <div
    style={{
      marginTop: "20px",
      padding: "20px",
      borderRadius: "12px",
      background: "#1e1e1e",
      border: "1px solid #444",
      color: "white",
      width: "600px",
    }}
  >
    <h4 style={{ marginBottom: "15px", fontSize: "18px" }}>
      ✅ Upload Successful
    </h4>

    <p style={{ margin: "8px 0" }}>
      <b>File ID:</b>{" "}
      <span style={{ color: "#22c55e" }}>{uploadResult.file_id}</span>
    </p>

    <p style={{ margin: "8px 0" }}>
      <b>Chunks Stored:</b>{" "}
      <span style={{ color: "#60a5fa" }}>{uploadResult.chunks_stored}</span>
    </p>

    <p style={{ margin: "8px 0", color: "#aaa" }}>
      PDF stored successfully in vector database.
    </p>

    <button
      onClick={() => navigator.clipboard.writeText(uploadResult.file_id)}
      style={{
        marginTop: "12px",
        padding: "10px 15px",
        borderRadius: "8px",
        background: "#2563eb",
        color: "white",
        fontWeight: "bold",
        cursor: "pointer",
        border: "none",
      }}
    >
      Copy File ID
    </button>
  </div>
)}

        </div>
      )}

      {/* Chat */}
{activeTab === "chat" && (
  <div>
    <h3>Student Chat</h3>

    <div
      style={{
        height: "400px",
        overflowY: "auto",
        border: "1px solid gray",
        padding: "10px",
        borderRadius: "8px",
        background: "#111",
      }}
    >
      {messages.map((m, idx) => (
        <div
          key={idx}
          style={{
            textAlign: m.role === "user" ? "right" : "left",
            marginBottom: "10px",
          }}
        >
          <span
            style={{
              display: "inline-block",
              padding: "10px",
              borderRadius: "10px",
              maxWidth: "70%",
              background: m.role === "user" ? "#2563eb" : "#333",
              color: "white",
            }}
          >
            {m.text}
          </span>
        </div>
      ))}
    </div>

    <br />

    <textarea
      rows="2"
      cols="80"
      value={question}
      onChange={(e) => setQuestion(e.target.value)}
      placeholder="Ask a question..."
    />

    <br />
    <button onClick={handleAsk}>Send</button>
  </div>
)}


      {/* Summary */}
      {activeTab === "summary" && (
        <div>
          <h3>Summarize PDF</h3>
          <button onClick={handleSummarize}>Summarize</button>

          {summaryResult && (
  <div
    style={{
      marginTop: "20px",
      padding: "20px",
      borderRadius: "12px",
      background: "#1e1e1e",
      border: "1px solid #444",
      color: "white",
      width: "90%",
      maxWidth: "900px",
      lineHeight: "1.6",
    }}
  >
    <h4 style={{ marginBottom: "15px", fontSize: "18px" }}>
      📌 Summary Output
    </h4>

    <div
      style={{
        background: "#111",
        padding: "15px",
        borderRadius: "10px",
        border: "1px solid #333",
        whiteSpace: "pre-wrap",
        color: "#e5e5e5",
        fontSize: "15px",
      }}
    >
      {summaryResult.summary}
    </div>

    <button
      onClick={() => navigator.clipboard.writeText(summaryResult.summary)}
      style={{
        marginTop: "15px",
        padding: "10px 15px",
        borderRadius: "8px",
        background: "#2563eb",
        color: "white",
        fontWeight: "bold",
        cursor: "pointer",
        border: "none",
      }}
    >
      Copy Summary
    </button>
  </div>
)}

        </div>
      )}

     {/* Quiz */}
{activeTab === "quiz" && (
  <div>
    <h3>Quiz Generator</h3>

    <label>Student ID: </label>
    <input
      value={studentId}
      onChange={(e) => setStudentId(e.target.value)}
      style={{ marginLeft: "10px", padding: "5px" }}
    />
    <br /><br />

    <label>Number of Questions: </label>
    <input
      type="number"
      value={quizCount}
      onChange={(e) => setQuizCount(parseInt(e.target.value))}
      style={{ marginLeft: "10px", padding: "5px", width: "80px" }}
    />
    <br /><br />

    <button
      onClick={handleGenerateQuiz}
      style={{
        padding: "10px 20px",
        borderRadius: "8px",
        background: "#2563eb",
        color: "white",
        fontWeight: "bold",
        cursor: "pointer",
        border: "none",
      }}
    >
      Generate Quiz
    </button>
      <button
  onClick={handleGenerateAdaptiveQuiz}
  style={{
    padding: "10px 20px",
    borderRadius: "8px",
    background: "#f97316",
    color: "white",
    fontWeight: "bold",
    cursor: "pointer",
    border: "none",
    marginLeft: "10px",
  }}
>
  Generate Adaptive Quiz
</button>

    {quizResult && (
      <div style={{ marginTop: "20px" }}>
        <h4 style={{ marginBottom: "10px" }}>Quiz</h4>

        {quizResult.map((q, idx) => (
          <div
            key={idx}
            style={{
              marginBottom: "20px",
              padding: "15px",
              borderRadius: "10px",
              border: "1px solid #444",
              background: "#1e1e1e",
              color: "white",
            }}
          >
            <div style={{ fontSize: "16px", fontWeight: "bold", marginBottom: "10px" }}>
              {idx + 1}. {q.question}
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {Object.entries(q.options).map(([key, val]) => (
                <label
                  key={key}
                  style={{
                    padding: "8px",
                    borderRadius: "8px",
                    border: "1px solid #333",
                    cursor: "pointer",
                    background: quizAnswers[q.question] === key ? "#2563eb" : "#111",
                    color: "white",
                  }}
                >
                  <input
                    type="radio"
                    name={q.question}
                    value={key}
                    checked={quizAnswers[q.question] === key}
                    onChange={() =>
                      setQuizAnswers({ ...quizAnswers, [q.question]: key })
                    }
                    style={{ marginRight: "10px" }}
                  />
                  <b>{key}.</b> {val}
                </label>
              ))}
            </div>
          </div>
        ))}

        <button
          onClick={handleSubmitQuiz}
          style={{
            padding: "10px 20px",
            borderRadius: "8px",
            background: "#22c55e",
            color: "black",
            fontWeight: "bold",
            cursor: "pointer",
            border: "none",
          }}
        >
          Submit Quiz
        </button>
      </div>
    )}

    {submitResult && (
      <div
        style={{
          marginTop: "20px",
          padding: "15px",
          borderRadius: "10px",
          background: "#111",
          border: "1px solid #444",
          color: "white",
          fontSize: "18px",
        }}
      >
        <h4>Result</h4>
        <p><b>Score:</b> {submitResult.score}</p>
        <p><b>Percentage:</b> {submitResult.percentage}%</p>
      </div>
    )}
  </div>
)}

      {/* Progress */}
{activeTab === "progress" && (
  <div>
    <h3>Student Progress</h3>

    <label>Student ID: </label>
    <input
      value={studentId}
      onChange={(e) => setStudentId(e.target.value)}
      style={{ marginLeft: "10px", padding: "5px" }}
    />
    <br /><br />

    <button
      onClick={handleProgress}
      style={{
        padding: "10px 20px",
        borderRadius: "8px",
        background: "#2563eb",
        color: "white",
        fontWeight: "bold",
        cursor: "pointer",
        border: "none",
      }}
    >
      Get Progress
    </button>

    {progressResult && (
      <div style={{ marginTop: "20px" }}>
        {/* Stats Card */}
        <div
          style={{
            padding: "15px",
            borderRadius: "10px",
            background: "#1e1e1e",
            border: "1px solid #444",
            color: "white",
            marginBottom: "20px",
          }}
        >
          <h4 style={{ marginBottom: "10px" }}>Stats</h4>
          <p><b>Total Attempted:</b> {progressResult.total_attempted}</p>
          <p><b>Correct:</b> {progressResult.correct}</p>
          <p><b>Accuracy:</b> {progressResult.accuracy}%</p>
        </div>

        {/* Wrong Questions */}
        <div
          style={{
            padding: "15px",
            borderRadius: "10px",
            background: "#1e1e1e",
            border: "1px solid #444",
            color: "white",
            marginBottom: "20px",
          }}
        >
          <h4 style={{ marginBottom: "10px" }}>Wrong Questions</h4>

          {progressResult.wrong_questions.length === 0 ? (
            <p>No wrong answers yet 🎉</p>
          ) : (
            progressResult.wrong_questions.map((w, idx) => (
              <div
                key={idx}
                style={{
                  marginBottom: "12px",
                  padding: "10px",
                  borderRadius: "8px",
                  background: "#111",
                  border: "1px solid #333",
                }}
              >
                <p style={{ margin: 0 }}><b>Q:</b> {w.question}</p>
                <p style={{ margin: 0 }}><b>Your Answer:</b> {w.selected}</p>
                <p style={{ margin: 0 }}><b>Correct Answer:</b> {w.correct}</p>
              </div>
            ))
          )}
        </div>

        {/* Roadmap */}
        <div
          style={{
            padding: "15px",
            borderRadius: "10px",
            background: "#1e1e1e",
            border: "1px solid #444",
            color: "white",
          }}
        >
          <h4 style={{ marginBottom: "10px" }}>Personalized Roadmap</h4>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              background: "#111",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #333",
              color: "white",
            }}
          >
            {progressResult.personalized_roadmap}
          </pre>
        </div>
      </div>
    )}
  </div>
)}

    </div>
  );
}
