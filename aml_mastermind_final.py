import streamlit as st
import json
import random
import time
from datetime import datetime
import os

st.set_page_config(page_title="AML Mastermind", layout="centered")

# --- Constants ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"
RESULTS_FILE = "leaderboard.json"

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- Init Session State ---
defaults = {
    "step": "auth", "authenticated": False, "player_name": "", "mode": None,
    "category": None, "questions": [], "answers": [], "current": 0,
    "start_time": None, "max_time": 0, "done": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Auth Step ---
if st.session_state.step == "auth":
    st.title("🔐 AML Mastermind Deluxe")
    pw = st.text_input("Enter password to continue:", type="password")
    if st.button("Login") and pw == PASSWORD:
        st.session_state.authenticated = True
        st.session_state.step = "intro"
    elif pw:
        st.error("Wrong password.")
    st.stop()

# --- Load Questions ---
questions_data = load_questions()
categories = group_by_category(questions_data)

# --- Intro Step ---
if st.session_state.step == "intro":
    st.title("🎯 AML Mastermind Deluxe")
    name = st.text_input("Enter your name to start:", value=st.session_state.player_name)
    if st.button("Confirm Name") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.step = "mode"
    st.stop()

# --- Mode Selection ---
if st.session_state.step == "mode":
    st.title("🎮 Game Setup")
    st.session_state.mode = st.radio("Choose your mode:", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Select a category:", list(categories.keys()))
    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of questions", 5, 30, 10)
    else:
        st.session_state.max_time = st.radio("Time limit (seconds):", [60, 120, 180])
    if st.button("Start Game"):
        all_q = categories.get(st.session_state.category, [])
        if not all_q:
            st.error("❌ No questions found in this category.")
            st.stop()
        random.shuffle(all_q)
        st.session_state.questions = (
            all_q[:st.session_state.num_questions] if st.session_state.mode == "Classic Quiz" else all_q
        )
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"
    st.stop()

# --- Quiz Step ---
if st.session_state.step == "quiz":
    questions = st.session_state.questions
    i = st.session_state.current
    mode = st.session_state.mode

    if mode == "Time Attack":
        elapsed = int(time.time() - st.session_state.start_time)
        time_left = st.session_state.max_time - elapsed
        st.markdown(f"⏳ Time left: **{time_left} seconds**")
        if time_left <= 0 or i >= len(questions):
            st.session_state.done = True
            st.session_state.step = "result"
            st.stop()

    if i < len(questions):
        q = questions[i]
        submitted_key = f"submitted_{i}"
        if submitted_key not in st.session_state:
            with st.form(key=f"form_{i}"):
                random.seed(q["id"])
                opts = q["options"].copy()
                random.shuffle(opts)
                sel = st.radio("Choose your answer:", opts, key=f"answer_{i}")
                submit = st.form_submit_button("Submit")

            if submit:
                correct = sel.strip().lower() == q["correct_answer"].strip().lower()
                st.session_state.answers.append(correct)
                st.session_state[submitted_key] = True
                if correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
                st.caption(f"**Explanation:** {q['explanation']}  \n\n🔗 **Source:** {q['source']}")
        else:
            if st.button("Next"):
                st.session_state.current += 1
                if mode == "Classic Quiz" and st.session_state.current >= len(questions):
                    st.session_state.done = True
                    st.session_state.step = "result"
    else:
        st.session_state.step = "result"

# --- Result Step ---
if st.session_state.step == "result":
    st.title("🏁 Quiz Completed")
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time)

    if total:
        percent = round(score / total * 100)
        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%) in {duration} seconds")
        if percent >= 75:
            st.success(f"🏅 Congratulations, {st.session_state.player_name}! You earned a certificate!")
        else:
            st.info("📘 Keep practicing to improve your score.")
    else:
        st.warning("⚠️ No questions were answered.")

    new_entry = {
        "name": st.session_state.player_name,
        "score": score,
        "total": total,
        "duration": duration,
        "category": st.session_state.category,
        "mode": st.session_state.mode,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    leaderboard = []
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            leaderboard = json.load(f)

    leaderboard.append(new_entry)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)

    if st.checkbox("📊 Show Leaderboard"):
        sorted_board = sorted(leaderboard, key=lambda x: x["score"], reverse=True)
        for r in sorted_board[:10]:
            pct = round(r["score"] / r["total"] * 100) if r["total"] else 0
            st.markdown(
                f"- {r['timestamp']} | {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} ({pct}%) in {r['duration']}s"
            )

    if st.button("Play Again"):
        for k in defaults:
            st.session_state.pop(k, None)
        st.experimental_rerun()

# --- Footer ---
st.markdown("---")
st.caption("© 2025 – AML Mastermind. Powered by FATF / IOSCO / IMF best practices.")
