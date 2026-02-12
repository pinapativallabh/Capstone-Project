import sqlite3
import os

DB_FOLDER = "data"
DB_NAME = os.path.join(DB_FOLDER, "students.db")

os.makedirs(DB_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT,
        file_id TEXT,
        question TEXT,
        selected_option TEXT,
        correct_option TEXT,
        is_correct INTEGER
    )
    """)

    conn.commit()
    conn.close()


def save_result(student_id, file_id, question, selected_option, correct_option, is_correct):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO quiz_results (student_id, file_id, question, selected_option, correct_option, is_correct)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, file_id, question, selected_option, correct_option, is_correct))

    conn.commit()
    conn.close()


def get_student_stats(student_id, file_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) FROM quiz_results
    WHERE student_id=? AND file_id=?
    """, (student_id, file_id))
    total = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM quiz_results
    WHERE student_id=? AND file_id=? AND is_correct=1
    """, (student_id, file_id))
    correct = cur.fetchone()[0]

    conn.close()

    return total, correct

def get_wrong_questions(student_id, file_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT question, selected_option, correct_option
    FROM quiz_results
    WHERE student_id=? AND file_id=? AND is_correct=0
    """, (student_id, file_id))

    rows = cur.fetchall()
    conn.close()

    return rows

def get_all_students(file_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT DISTINCT student_id
    FROM quiz_results
    WHERE file_id=?
    """, (file_id,))

    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]

def get_student_summary(student_id, file_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT COUNT(*) FROM quiz_results
    WHERE student_id=? AND file_id=?
    """, (student_id, file_id))
    total = cur.fetchone()[0]

    cur.execute("""
    SELECT COUNT(*) FROM quiz_results
    WHERE student_id=? AND file_id=? AND is_correct=1
    """, (student_id, file_id))
    correct = cur.fetchone()[0]

    conn.close()

    accuracy = (correct / total) * 100 if total > 0 else 0
    return total, correct, accuracy
def get_recent_wrong_questions(student_id, file_id, limit=5):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT question
    FROM quiz_results
    WHERE student_id=? AND file_id=? AND is_correct=0
    ORDER BY id DESC
    LIMIT ?
    """, (student_id, file_id, limit))

    rows = cur.fetchall()
    conn.close()

    return [r[0] for r in rows]
def get_wrong_summary(student_id, file_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    SELECT question, COUNT(*) as times_wrong
    FROM quiz_results
    WHERE student_id=? AND file_id=? AND is_correct=0
    GROUP BY question
    ORDER BY times_wrong DESC
    """, (student_id, file_id))

    rows = cur.fetchall()
    conn.close()

    return rows
