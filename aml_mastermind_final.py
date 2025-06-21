import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import pathlib

# CONFIG
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- UTILITIES ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

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
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Excellent performance!")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "Areas to Improve (based on incorrect answers):")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', '')}"
            ]
            for line in lines:
                for chunk in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(110, y, chunk)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
        categories = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for cat in categories:
            c.setFont("Helvetica", 10)
            c.drawString(120, y, f"- {cat}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 80
    c.save()
    buffer.seek(0)
    return buffer

# STATE INIT
def init_state():
    keys = {
        "page": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "submitted": False,
        "selected_answer": None,
        "start_time": None,
        "time_limit": None,
        "score": 0,
        "game_over": False,
        "leaderboard_saved": False,
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

# APP START
st.set_page_config("AML Serious Game", layout="centered")
init_state()

questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

# PAGE: NAME
if st.session_state.page == "name":
    st.title("🎓 AML Serious Game for Supervisors")
    st.markdown(f"👥 Players who already played: **{player_count}**")
    st.session_state.player_name = st.text_input("Enter your name:")
    if st.session_state.player_name.strip():
        if st.button("Continue"):
            st.session_state.page = "intro"
    st.stop()

# PAGE: INSTRUCTIONS
if st.session_state.page == "intro":
    st.markdown("## 🕵️ Welcome to the AML Serious Game")
    st.markdown("""
    **🚨 Mission**: Test your AML skills through real-world questions.

    - 🧠 Learn AML/CFT from Crypto, Funds, and Banking
    - ⏱️ Choose Classic or Time Attack
    - 📜 Get a certificate
    - 🏆 Join the leaderboard

    ### Disclaimer:
    This quiz is for educational purposes only. There may be simplifications and inaccuracies. Nothing here constitutes legal advice.
    """)
    if st.button("Start"):
        st.session_state.page = "config"
    st.stop()

# PAGE: GAME CONFIG
if st.session_state.page == "config":
    st.subheader("Choose game mode and topic")
    st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Topic", list(grouped.keys()))
    if st.session_state.mode == "Classic Quiz":
        num_qs = st.slider("Number of questions", 5, 30, 10)
        st.session_state.questions = random.sample(grouped[st.session_state.category], k=num_qs)
        st.session_state.time_limit = None
    else:
        st.session_state.questions = grouped[st.session_state.category]
        st.session_state.time_limit = st.selectbox("Time limit (s)", TIME_OPTIONS)
    if st.button("Start Game"):
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
    st.stop()

# PAGE: QUIZ
if st.session_state.page == "quiz":
    if st.session_state.time_limit:
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
        else:
            st.markdown(f"⏳ Time left: **{remaining} seconds**")

    if st.session_state.current >= len(st.session_state.questions):
        st.session_state.page = "results"
        st.stop()

    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"### Question {st.session_state.current + 1}: {q['question']}")
    options = q["options"]
    st.session_state.selected_answer = st.radio("Choose your answer:", options, index=0, key=f"q_{st.session_state.current}")

    if not st.session_state.submitted:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = st.session_state.selected_answer.strip().lower()
            st.session_state.answers.append(picked == correct)
            st.session_state.submitted = True
            st.success("✅ Correct!" if picked == correct else f"❌ Wrong. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.submitted = False
            st.session_state.selected_answer = None
    st.stop()

# PAGE: RESULTS
if st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## 🎯 Game Complete")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} seconds")

    if not st.session_state.leaderboard_saved:
        append_to_json(LEADERBOARD_PATH, {
            "name": st.session_state.player_name.strip()[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.session_state.leaderboard_saved = True

    incorrect = [st.session_state.questions[i] for i, correct in enumerate(st.session_state.answers) if not correct]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Your Certificate", cert, "AML_Certificate.pdf", "application/pdf")

    with st.expander("🏅 Leaderboard"):
        top10 = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top10, start=1):
            st.markdown(
                f"{i}. {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} | {r['duration']}s"
            )

    st.markdown("---")
    st.subheader("💬 Leave a comment")
    comment = st.text_area("Your feedback (not visible to others):")
    if st.button("Submit Comment"):
        append_to_json(COMMENTS_PATH, {
            "name": st.session_state.player_name,
            "comment": comment,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.success("Comment submitted!")

    st.markdown("_(Comments are only visible to the creator, not other players.)_")

    st.markdown("---")
    if st.text_input("Admin password", type="password") == PASSWORD:
        st.subheader("🛡️ Comments (Admin only)")
        for c in load_json(COMMENTS_PATH):
            st.markdown(f"**{c.get('name', 'Anon')}** ({c.get('time', 'N/A')})")
            st.markdown(f"> {c.get('comment', '')}")
