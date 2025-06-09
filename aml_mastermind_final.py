import streamlit as st
import json
import random
import time
from datetime import datetime
import os

# --- Constants ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = "leaderboard.json"

# --- Setup ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- Load and group questions ---
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

def save_score_to_leaderboard(player_name, mode, category, score, total, duration):
    record = {
        "name": player_name,
        "mode": mode,
        "category": category,
        "score": score,
        "total": total,
        "duration": duration,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    leaderboard = []
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            leaderboard = json.load(f)
    leaderboard.append(record)
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# --- Auth ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 AML Mastermind Deluxe")
    password = st.text_input("Enter the password:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.stop()

# --- Name input ---
st.title("🧠 AML Mastermind Deluxe")
if "player_name" not in st.session_state:
    st.session_state.player_name = ""

st.session_state.player_name = st.text_input("Enter your name (or pseudonym):", value=st.session_state.player_name)

if not st.session_state.player_name.strip():
    st.warning("Please enter a name to proceed.")
    st.stop()

# --- Question loading ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- Game session defaults ---
for key, default in {
    "mode": None, "category": None, "questions": [],
    "current": 0, "answers": [], "start_time": None, "timer_limit": 120,
    "game_ended": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Game Mode Selection ---
if st.session_state.mode is None:
    st.subheader("🎮 Choose your game mode")
    st.session_state.mode = st.selectbox("Game Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Category", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        st.session_state.timer_limit = st.radio("Time limit", [60, 120, 180], index=1)

    if st.button("Start Game"):
        pool = grouped.get(st.session_state.category, [])
        random.shuffle(pool)
        st.session_state.questions = pool
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time() if st.session_state.mode == "Time Attack" else None
        st.session_state.game_ended = False

# --- Classic Quiz Mode ---
if st.session_state.mode == "Classic Quiz" and not st.session_state.game_ended:
    if st.session_state.current < st.session_state.num_questions:
        q = st.session_state.questions[st.session_state.current]
        st.markdown(f"**Question {st.session_state.current+1}/{st.session_state.num_questions}**")
        st.markdown(f"### {q['question']}")
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"classic_{st.session_state.current}")
        if st.button("Submit Answer"):
            correct = selected == q["correct_answer"]
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.info(f"📘 {q.get('explanation', '')}  \n🔗 **Source:** {q.get('source', '')}")
            st.session_state.current += 1
    else:
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        duration = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
        st.session_state.game_ended = True
        st.subheader("🎯 Quiz Completed")
        st.markdown(f"### 🧮 Score: {score}/{total} ({round(score/total*100)}%)" if total else "No score recorded.")
        if score / total >= 0.75:
            st.success("🏅 Congratulations! You earned a certificate!")
        else:
            st.warning("📘 Try again to improve your score.")
        save_score_to_leaderboard(st.session_state.player_name, "Classic Quiz", st.session_state.category, score, total, duration)
        if st.button("Play Again"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.experimental_rerun()

# --- Time Attack Mode ---
elif st.session_state.mode == "Time Attack" and not st.session_state.game_ended:
    time_left = st.session_state.timer_limit - int(time.time() - st.session_state.start_time)
    if time_left <= 0 or st.session_state.current >= len(st.session_state.questions):
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        st.session_state.game_ended = True
        st.subheader("⏱️ Time's up!")
        st.markdown(f"### 🧮 Score: {score}/{total} ({round(score/total*100)}%)" if total else "No score recorded.")
        if score >= 10:
            st.success("🏅 Great job! Certificate earned!")
        else:
            st.info("📘 Keep practicing to improve.")
        save_score_to_leaderboard(st.session_state.player_name, "Time Attack", st.session_state.category, score, total, st.session_state.timer_limit)
        if st.button("Play Again"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.experimental_rerun()
    else:
        q = st.session_state.questions[st.session_state.current]
        st.markdown(f"⏳ **Time Left: {time_left} seconds**")
        st.markdown(f"### {q['question']}")
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"time_{st.session_state.current}")
        if st.button("Submit Answer"):
            correct = selected == q["correct_answer"]
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.info(f"📘 {q.get('explanation', '')}  \n🔗 **Source:** {q.get('source', '')}")
            st.session_state.current += 1

# --- Leaderboard ---
with st.expander("📊 Show Leaderboard"):
    leaderboard = load_leaderboard()
    if leaderboard:
        for r in reversed(leaderboard[-20:]):
            pct = round(r['score'] / r['total'] * 100) if r['total'] else 0
            st.markdown(f"- {r['timestamp']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} ({pct}%) in {r['duration']}s")
    else:
        st.info("No scores recorded yet.")
