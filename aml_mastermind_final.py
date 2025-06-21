import streamlit as st
import json
import random
import time
import os
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pathlib

# Paths
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
QUESTIONS_PATH = "questions_cleaned.json"

# Admin password
ADMIN_PASSWORD = "iloveaml2025"

# --- Utility Functions ---
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

# --- Certificate ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏆 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.drawString(100, y, "🎉 Great job! You've demonstrated strong AML knowledge.")
    else:
        c.drawString(100, y, "🔍 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation.')}"
            ]
            for line in lines:
                for i in range(0, len(line), 100):
                    c.drawString(110, y, line[i:i+100])
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- Streamlit Setup ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

questions_data = load_questions()

# --- App Pages ---
if "page" not in st.session_state:
    st.session_state.page = "name"

# --- Page: Name Entry ---
if st.session_state.page == "name":
    st.title("🕵️ AML Serious Game")
    st.write("Please enter your name to start:")
    name = st.text_input("Your name:")
    if name:
        st.session_state.name = name.strip()
        st.session_state.page = "intro"
        st.rerun()

# --- Page: Instructions ---
elif st.session_state.page == "intro":
    st.title("📘 How to Play")
    st.markdown(f"👤 Players so far: **{len(load_json(LEADERBOARD_PATH))}**")
    st.markdown("""
### 🚨 Your Mission:
Test your AML/CFT knowledge in Banking, Crypto, or Investment Funds.

### 🛠️ Game Modes:
- **Classic Quiz**: Choose # of questions
- **Time Attack**: Beat the clock!

📜 You’ll get:
- Certificate
- Leaderboard placement
- Personalized feedback

📝 Disclaimer:
This quiz is for educational purposes. It may include simplifications and does not constitute legal advice.
""")
    if st.button("Start Quiz"):
        st.session_state.page = "settings"
        st.rerun()

# --- Page: Game Settings ---
elif st.session_state.page == "settings":
    st.title("🎮 Choose Game Settings")
    mode = st.selectbox("Select mode", ["Classic Quiz", "Time Attack"])
    categories = sorted(list(set(q.get("category", "Other") for q in questions_data)))
    category = st.selectbox("Select topic", categories)
    time_limit = st.selectbox("Time Limit (for Time Attack)", [60, 120, 180]) if mode == "Time Attack" else None
    num_questions = st.slider("Number of Questions", 5, 30, 10) if mode == "Classic Quiz" else None
    if st.button("Launch Game"):
        questions = [q for q in questions_data if q.get("category") == category]
        random.shuffle(questions)
        st.session_state.questions = questions[:num_questions] if mode == "Classic Quiz" else questions
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.start_time = time.time()
        st.session_state.time_limit = time_limit
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.feedback_shown = False
        st.session_state.page = "quiz"
        st.rerun()

# --- Page: Quiz ---
elif st.session_state.page == "quiz":
    i = st.session_state.current
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
            st.rerun()
        st.info(f"⏱ Time left: {remaining} seconds")

    q = st.session_state.questions[i]
    st.subheader(f"Question {i+1}/{len(st.session_state.questions)}")
    st.markdown(q["question"])

    if f"options_{i}" not in st.session_state:
        st.session_state[f"options_{i}"] = q["options"]

    selected = st.radio("Your answer:", st.session_state[f"options_{i}"], key=f"radio_{i}")

    if not st.session_state.get("feedback_shown", False):
        if st.button("Submit"):
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(is_correct)
            st.session_state.feedback_shown = True
            st.success("✅ Correct!" if is_correct else f"❌ Wrong. Correct: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.feedback_shown = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"
            st.rerun()

# --- Page: Results ---
elif st.session_state.page == "results":
    total = len(st.session_state.questions)
    score = sum(st.session_state.answers)
    percent = round(100 * score / total)
    duration = int(time.time() - st.session_state.start_time)

    st.title("📊 Results")
    st.markdown(f"👤 **{st.session_state.name}**")
    st.markdown(f"🎯 Score: **{score}/{total}** ({percent}%)")
    st.markdown(f"⏱ Time: **{duration} seconds**")
    st.markdown(f"📚 Topic: {st.session_state.category}")
    st.markdown(f"🎮 Mode: {st.session_state.mode}")

    record = {
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    append_json(LEADERBOARD_PATH, record)

    incorrect = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Certificate", cert, "AML_Certificate.pdf", "application/pdf")

    st.markdown("---")
    if st.checkbox("🏆 Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, p in enumerate(top, 1):
            st.markdown(f"{i}. {p['name']} | {p['score']}/{p['total']} | {p['duration']}s")

    st.markdown("---")
    st.markdown("💬 Leave a private comment for the game creator:")
    comment = st.text_area("Your comment")
    if st.button("Submit Comment"):
        append_json(COMMENTS_PATH, {"name": st.session_state.name, "comment": comment, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        st.success("Comment submitted! Only the game creator can see it.")

    st.markdown("🔒 Comments are private and not visible to other players.")

    if st.text_input("Admin password") == ADMIN_PASSWORD:
        st.subheader("📥 All Comments (Admin Only)")
        for c in load_json(COMMENTS_PATH):
            st.markdown(f"**{c['name']}** ({c['time']})")
            st.markdown(f"👉 {c['comment']}")
            st.markdown("---")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
