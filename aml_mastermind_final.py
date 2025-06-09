import streamlit as st
import json
import random
import time
import uuid
import os
from datetime import datetime

# --- Constants ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = "leaderboard.json"

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_questions_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- Save leaderboard entry ---
def save_result(mode, category, score, total, duration):
    result = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "category": category,
        "score": score,
        "total": total,
        "percent": round(score / total * 100) if total > 0 else 0,
        "duration": duration
    }
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
    data.append(result)
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- Load leaderboard ---
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# --- Streamlit Setup ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")
st.title("🕵️ AML Mastermind Deluxe")

# --- Password ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter the password to play:", type="password")
    if password:
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.experimental_rerun()
        else:
            st.error("Incorrect password")
    st.stop()

# --- Load & prepare questions ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- Game Session ---
for key, default in {
    "mode": None, "category": None, "questions": [],
    "current": 0, "answers": [], "start_time": None,
    "duration_limit": 120
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Game Mode Selection ---
if st.session_state.mode is None:
    st.subheader("🎮 Choose Your Game Mode")
    st.session_state.mode = st.selectbox("Game Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Select a Category", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        q_count = st.slider("Number of Questions", 5, 30, 10)
        st.session_state.question_count = q_count
    else:
        st.session_state.duration_limit = st.selectbox("Select Time Limit", [60, 120, 180])

    if st.button("▶️ Start Game"):
        available = grouped.get(st.session_state.category, [])
        random.shuffle(available)
        st.session_state.questions = available[:st.session_state.question_count] if st.session_state.mode == "Classic Quiz" else available
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.experimental_rerun()

# --- Classic Quiz Mode ---
elif st.session_state.mode == "Classic Quiz":
    i = st.session_state.current
    if i < len(st.session_state.questions):
        q = st.session_state.questions[i]
        with st.form(key=f"classic_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            opts = q["options"].copy()
            random.shuffle(opts)
            selected = st.radio("Choose:", opts, key=f"answer_{i}")
            submit = st.form_submit_button("Submit")
        if submit:
            correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.experimental_rerun()
    else:
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        duration = int(time.time() - st.session_state.start_time)
        percent = round(score / total * 100) if total > 0 else 0

        save_result("Classic", st.session_state.category, score, total, duration)

        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%)")
        st.markdown(f"⏱️ Duration: {duration} sec")

        if percent >= 75:
            st.success("🏆 Certificate earned!")
        else:
            st.warning("Keep training to earn a certificate.")

        if st.button("🔁 Play Again"):
            for k in ["mode", "category", "questions", "current", "answers"]:
                del st.session_state[k]
            st.experimental_rerun()

# --- Time Attack Mode ---
elif st.session_state.mode == "Time Attack":
    if st.session_state.start_time is None:
        st.session_state.start_time = time.time()

    now = time.time()
    elapsed = int(now - st.session_state.start_time)
    remaining = st.session_state.duration_limit - elapsed

    if remaining <= 0 or st.session_state.current >= len(st.session_state.questions):
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        duration = st.session_state.duration_limit
        save_result("Time Attack", st.session_state.category, score, total, duration)

        st.markdown(f"### ⌛ Time's up!")
        st.markdown(f"### 🧮 Score: {score} questions answered")
        if score >= 10:
            st.success("🏆 Certificate earned!")
        else:
            st.info("Try again for a higher score!")

        if st.button("🔁 Play Again"):
            for k in ["mode", "category", "questions", "current", "answers", "start_time"]:
                del st.session_state[k]
            st.experimental_rerun()
    else:
        i = st.session_state.current
        q = st.session_state.questions[i]
        st.markdown(f"⏳ Time Left: **{remaining} sec**")
        with st.form(key=f"time_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            opts = q["options"].copy()
            random.shuffle(opts)
            selected = st.radio("Choose:", opts, key=f"answer_time_{i}")
            submit = st.form_submit_button("Submit")
        if submit:
            correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.experimental_rerun()

# --- Leaderboard ---
st.markdown("---")
with st.expander("📊 View Leaderboard"):
    leaderboard = load_leaderboard()
    if leaderboard:
        sorted_data = sorted(leaderboard, key=lambda x: (-x['percent'], x['duration']))
        for i, entry in enumerate(sorted_data[:10], start=1):
            st.markdown(
                f"{i}. **{entry['mode']}** | {entry['category']} | "
                f"**{entry['score']}/{entry['total']}** ({entry['percent']}%) – {entry['duration']}s "
                f"at _{entry['timestamp']}_"
            )
    else:
        st.info("No games played yet.")

# --- Footer ---
st.markdown("---")
st.caption("Built for AML/CFT training | Powered by FATF, IOSCO, IMF, World Bank best practices.")
