import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# --- File paths ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
QUESTIONS_PATH = "questions_cleaned.json"
ADMIN_PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- Functions ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, item):
    data = load_json(path)
    data.append(item)
    save_json(path, data)

def generate_certificate(name, score, total, percent, duration, incorrect):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w / 2, h - 100, "🎓 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, h - 140, f"Name: {name}")
    c.drawString(100, h - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, h - 180, f"Duration: {duration} sec")
    c.drawString(100, h - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = h - 240
    if percent < 75:
        c.drawString(100, y, "Areas to review:")
        y -= 20
        for q in incorrect:
            lines = [f"Q: {q['question']}", f"✔ {q['correct_answer']} - {q.get('explanation','')[:80]}"]
            for line in lines:
                c.drawString(110, y, line[:90])
                y -= 15
                if y < 80:
                    c.showPage()
                    y = h - 80
    c.save()
    buffer.seek(0)
    return buffer

# --- App Setup ---
st.set_page_config("AML Quiz", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "start"

# --- Pages ---
if st.session_state.page == "start":
    st.title("🕵️ AML Mastermind")
    st.markdown("Welcome to the AML Serious Game for Supervisors!")
    st.session_state.name = st.text_input("Enter your name:")
    if st.button("Start"):
        if st.session_state.name.strip():
            st.session_state.page = "config"

elif st.session_state.page == "config":
    questions = load_json(QUESTIONS_PATH)
    categories = sorted(set(q.get("category", "Other") for q in questions))
    st.session_state.mode = st.selectbox("Choose mode", ["Classic", "Time Attack"])
    st.session_state.category = st.selectbox("Choose category", categories)
    if st.session_state.mode == "Classic":
        st.session_state.num_questions = st.slider("Number of questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time limit (seconds)", TIME_OPTIONS)
        st.session_state.num_questions = 100
    if st.button("Begin Quiz"):
        pool = [q for q in questions if q["category"] == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.feedback = False
        st.session_state.page = "quiz"

elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        st.markdown(f"⏳ Time left: **{remaining} sec**")
        if remaining <= 0:
            st.session_state.page = "results"
    q = st.session_state.questions[st.session_state.current]
    st.subheader(f"Question {st.session_state.current + 1}")
    st.markdown(q["question"])
    if f"opts_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"opts_{st.session_state.current}"] = opts
    opts = st.session_state[f"opts_{st.session_state.current}"]
    selected = st.radio("Options:", opts, key=f"radio_{st.session_state.current}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.is_correct = is_correct
            st.session_state.feedback = True
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", ""))
            st.caption(f"Source: {q.get('source', '')}")
    else:
        if st.button("Next"):
            st.session_state.answers.append(st.session_state.is_correct)
            st.session_state.feedback = False
            st.session_state.current += 1
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.success("🎉 Quiz Complete!")
    st.markdown(f"**Name:** {st.session_state.name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} sec")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")

    incorrect = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers) if not correct
    ]
    cert = generate_certificate(st.session_state.name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Certificate", cert, "certificate.pdf", "application/pdf")

    append_json(LEADERBOARD_PATH, {
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "duration": duration,
        "percent": percent,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "time": datetime.now().isoformat()
    })

    if st.checkbox("Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}")

    st.markdown("---")
    comment = st.text_area("🗣 Leave feedback (private)")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_PATH, {
            "name": st.session_state.name[:5] + "###",
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Comment submitted!")

    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Enter admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_json(COMMENTS_PATH)
        for c in comments:
            st.markdown(f"**{c['name']}** ({c['time']}): {c['comment']}")
        st.download_button("📥 Download All Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        st.session_state.clear()
