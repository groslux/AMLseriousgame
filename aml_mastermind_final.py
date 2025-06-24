import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# Constants
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# Load and save functions
def load_json(path, default=[]):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json(path, entry):
    data = load_json(path)
    data.append(entry)
    save_json(path, data)

# Certificate generator
def generate_certificate(name, score, total, percent, duration, wrong_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 80, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(80, height - 120, f"Name: {name}")
    c.drawString(80, height - 140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(80, height - 160, f"Duration: {duration} sec")
    c.drawString(80, height - 180, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 220
    if wrong_qs:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(80, y, "Review these questions:")
        y -= 20
        c.setFont("Helvetica", 10)
        for q in wrong_qs:
            c.drawString(90, y, f"Q: {q['question']}")
            y -= 12
            c.drawString(100, y, f"✔ Correct: {q['correct_answer']}")
            y -= 12
            c.drawString(100, y, f"ℹ {q.get('explanation', '')}")
            y -= 30
            if y < 100:
                c.showPage()
                y = height - 100
    c.save()
    buffer.seek(0)
    return buffer

# Initialize session state
if "page" not in st.session_state:
    st.session_state.page = "name"
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False

# Page: Name input
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    st.markdown("### Enter your name to start")
    player_name = st.text_input("Your name")
    if st.button("Continue") and player_name.strip():
        st.session_state.player_name = player_name.strip()
        st.session_state.page = "instructions"

# Page: Instructions
elif st.session_state.page == "instructions":
    st.title("📘 Instructions")
    st.markdown("""
- You will answer multiple-choice questions on AML topics.
- First click on `Submit` shows feedback.  
- Second click on `Submit` moves to the next question.
- At the end: 🎓 Certificate, 🏆 Leaderboard, and 🗣️ Comment box.
    """)
    mode = st.selectbox("Choose mode", ["Classic", "Time Attack"])
    data = load_json(QUESTIONS_FILE)
    categories = sorted(set(q["category"] for q in data))
    category = st.selectbox("Select category", categories)
    if st.button("Start Quiz"):
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = [q for q in data if q["category"] == category]
        random.shuffle(st.session_state.questions)
        st.session_state.questions = st.session_state.questions[:10]
        st.session_state.page = "quiz"
        st.session_state.start_time = time.time()

# Page: Quiz
elif st.session_state.page == "quiz":
    total_qs = len(st.session_state.questions)
    current = st.session_state.current_q
    if current >= total_qs:
        st.session_state.page = "results"
        st.rerun()

    q = st.session_state.questions[current]
    st.subheader(f"Question {current + 1} of {total_qs}")
    st.write(q["question"])
    if f"options_{current}" not in st.session_state:
        options = q["options"].copy()
        random.shuffle(options)
        st.session_state[f"options_{current}"] = options
    selected = st.radio("Choose one:", st.session_state[f"options_{current}"], key=f"select_{current}")

    if st.button("Submit"):
        if not st.session_state.feedback_shown:
            st.session_state.feedback_shown = True
            st.session_state.selected = selected
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(is_correct)
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", ""))
            st.caption(f"Source: {q.get('source', '')}")
        else:
            st.session_state.current_q += 1
            st.session_state.feedback_shown = False
            st.rerun()

# Page: Results
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = int((score / total) * 100)
    duration = int(time.time() - st.session_state.start_time)
    wrong_qs = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]

    st.title("✅ Quiz Complete!")
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} seconds")
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, wrong_qs)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf", mime="application/pdf")

    append_to_json(LEADERBOARD_FILE, {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "duration": duration,
        "timestamp": datetime.now().isoformat(),
        "category": st.session_state.category
    })

    if st.checkbox("🏅 Show Leaderboard"):
        data = load_json(LEADERBOARD_FILE)
        top = sorted(data, key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, entry in enumerate(top, 1):
            st.markdown(f"{i}. **{entry['name']}** | {entry['score']} pts | {entry['duration']}s | {entry['category']}")

    st.markdown("---")
    st.markdown("### 🗣️ Leave a comment (visible only to the creator)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_to_json(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you! Your comment has been submitted.")
    st.caption("Comments are private and only visible to the game creator.")

    st.markdown("### 🔐 Admin Access")
    password = st.text_input("Password", type="password")
    if password == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        st.success("Access granted")
        if comments:
            for c in comments:
                st.markdown(f"**{c['name']}** ({c['time']}):")
                st.write(c["comment"])
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")
        else:
            st.info("No comments yet.")

    if st.button("🔄 Play Again"):
        st.session_state.clear()
        st.rerun()
