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

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]

# --- FILE UTILS ---
def load_json_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json_file(path, record):
    data = load_json_file(path)
    data.append(record)
    save_json_file(path, data)

# --- LEADERBOARD UTILS ---
def get_player_count():
    return len(load_json_file(LEADERBOARD_PATH))

def get_top_players():
    return sorted(load_json_file(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🔍 Areas to Improve (based on incorrect answers):")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica-Bold", 10)
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]
            for line in lines:
                wrapped = [line[i:i+100] for i in range(0, len(line), 100)]
                for subline in wrapped:
                    c.drawString(110, y, subline)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
        categories = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "📚 Suggested Topics to Review:")
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

# --- PAGE INIT ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- STATE ---
def init_state():
    defaults = {
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "game_started": False,
        "game_ended": False,
        "submitted": False,
        "feedback_displayed": False,
        "leaderboard_saved": False,
        "selected_answer": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

@st.cache_data
def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- INTRO ---
st.title("🕵️ AML Serious Game for Supervisors")
st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)
st.markdown("## 🔐 Enter your name to begin:")
st.session_state.player_name = st.text_input("Name:")
if not st.session_state.player_name.strip():
    st.stop()

st.markdown("""
### 🚨 Your Mission:
Test your AML supervision skills in a fun and interactive way.

### 🎮 Game Modes:
- Classic: Fixed number of questions
- Time Attack: Answer as many as you can before the timer runs out

### 📋 Topics:
- Crypto
- Investment Funds
- Banking

### 📝 Disclaimer:
This quiz is for training purposes only. Some questions may include simplifications or approximations and do not constitute legal advice.
""")

if not st.session_state.game_started:
    st.subheader("Select Game Mode")
    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Category", list(grouped.keys()))
    if mode == "Classic Quiz":
        num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped.get(category, [])
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.game_started = True
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.game_ended = False
        st.session_state.feedback_displayed = False
        st.session_state.submitted = False
        st.session_state.leaderboard_saved = False
    else:
        st.stop()

# --- GAME LOOP ---
if st.session_state.game_started and not st.session_state.game_ended:
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.game_ended = True

    if not st.session_state.game_ended and st.session_state.current < len(st.session_state.questions):
        q_idx = st.session_state.current
        question = st.session_state.questions[q_idx]
        if f"options_{q_idx}" not in st.session_state:
            options = question["options"].copy()
            random.shuffle(options)
            st.session_state[f"options_{q_idx}"] = options
        options = st.session_state[f"options_{q_idx}"]
        st.markdown(f"### Question {q_idx + 1}: {question['question']}")
        selected = st.radio("Choose your answer:", options, key=f"answer_{q_idx}")
        if st.button("Submit Answer", key=f"submit_{q_idx}"):
            st.session_state.selected_answer = selected
            correct = question["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.session_state.feedback_displayed = True
            st.session_state.submitted = True

        if st.session_state.feedback_displayed:
            correct = question["correct_answer"]
            if st.session_state.answers[-1]:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong. Correct answer: {correct}")
            st.info(question.get("explanation", "No explanation provided."))
            st.caption(f"📚 Source: {question.get('source', 'Unknown')}")
            if st.button("Next Question"):
                st.session_state.current += 1
                st.session_state.feedback_displayed = False

    if st.session_state.current >= len(st.session_state.questions):
        st.session_state.game_ended = True

# --- RESULTS ---
if st.session_state.game_ended:
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## 🎉 Quiz Complete!")
    st.markdown(f"**👤 Player:** {st.session_state.player_name}")
    st.markdown(f"**📚 Category:** {st.session_state.category}")
    st.markdown(f"**🏁 Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**⏱️ Duration:** {duration} seconds")

    if not st.session_state.leaderboard_saved:
        append_to_json_file(LEADERBOARD_PATH, {
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

    incorrect_qs = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers)
        if not correct
    ]
    cert_buffer = generate_certificate(
        st.session_state.player_name, score, total, percent, duration, incorrect_qs
    )
    st.download_button("📄 Download Your Certificate", data=cert_buffer, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("📊 Show Leaderboard"):
        for i, r in enumerate(get_top_players(), 1):
            st.markdown(
                f"{i}. {r['name']} | {r['category']} | {r['score']}/{r['total']} | {r['duration']}s"
            )

    st.markdown("## 💬 Leave a comment (private to the game creator)")
    comment = st.text_area("Your feedback:", max_chars=500)
    if st.button("Send Comment"):
        if comment.strip():
            append_to_json_file(COMMENTS_PATH, {
                "name": st.session_state.player_name,
                "timestamp": datetime.now().isoformat(),
                "comment": comment.strip()
            })
            st.success("Thanks for your feedback! Your comment has been saved.")

    st.markdown("---")
    st.caption("🛡️ Comments are private and will never be shown to other players.")
    st.caption("🔒 Designed for AML training of Supervisors - GROS - Luxembourg.")
