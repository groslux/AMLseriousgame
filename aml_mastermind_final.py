import streamlit as st
import json
import random
import time
from datetime import datetime
import os

# --- Configuration ---
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

def save_result(mode, category, score, total, duration):
    record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": mode,
        "category": category,
        "score": score,
        "total": total,
        "duration": duration
    }
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
    data.append(record)
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# --- UI Setup ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")
st.title("🕵️ AML Mastermind Deluxe")

# --- Password Protection ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    password = st.text_input("Enter the password to start:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.stop()

# --- Player Input ---
player_name = st.text_input("Enter your name (anonymous initials allowed):")
if not player_name.strip():
    st.warning("Please enter your name to continue.")
    st.stop()

# --- Load and Prepare Questions ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- Session Initialization ---
for k in ["mode", "category", "questions", "current", "answers", "start_time", "timer_limit"]:
    if k not in st.session_state:
        st.session_state[k] = None if k == "mode" else [] if k == "answers" else 0

# --- Mode Selection ---
if not st.session_state.mode:
    st.subheader("🎮 Choose your game mode")
    st.session_state.mode = st.selectbox("Game Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Category", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        count = st.slider("Select number of questions:", 5, 30, 10)
    else:
        st.session_state.timer_limit = st.selectbox("Select time limit (seconds):", [60, 120, 180])

    if st.button("Start Game"):
        pool = grouped[st.session_state.category]
        sample_size = count if st.session_state.mode == "Classic Quiz" else len(pool)
        st.session_state.questions = random.sample(pool, min(sample_size, len(pool)))
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []

# --- CLASSIC MODE ---
elif st.session_state.mode == "Classic Quiz":
    i = st.session_state.current
    if i < len(st.session_state.questions):
        q = st.session_state.questions[i]
        with st.form(f"form_classic_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            choices = q["options"].copy()
            random.shuffle(choices)
            picked = st.radio("Choose your answer:", choices)
            submitted = st.form_submit_button("Submit")
        if submitted:
            correct = picked.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.info(f"💡 {q['explanation']}")
            st.caption(f"📚 Source: {q['source']}")
            st.session_state.current += 1
    else:
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        if st.session_state.start_time:
            duration = int(time.time() - st.session_state.start_time)
else:
        duration = 0
        pct = round(score / total * 100) 
        if total > 0 
            save_result("Classic Quiz", st.session_state.category, score, total, duration)
            st.markdown(f"### ✅ Score: {score}/{total} ({pct}%)")
            st.markdown(f"🕓 Duration: {duration} sec")
        if pct >= 75:
            st.success("🏆 You passed! Certificate earned!")
        else:
            st.warning("🔁 Try again to score at least 75%!")
        if st.button("Play Again"):
            for k in ["mode", "category", "questions", "current", "answers", "start_time"]:
                del st.session_state[k]

# --- TIME ATTACK MODE ---
elif st.session_state.mode == "Time Attack":
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = st.session_state.timer_limit - elapsed
    if remaining <= 0 or st.session_state.current >= len(st.session_state.questions):
        score = sum(st.session_state.answers)
        total = len(st.session_state.answers)
        save_result("Time Attack", st.session_state.category, score, total, st.session_state.timer_limit)
        st.markdown(f"### ⏱️ Time's Up! Final Score: {score}")
        if score >= 10:
            st.success("🏆 Certificate earned!")
        else:
            st.info("Practice more to improve.")
        if st.button("Play Again"):
            for k in ["mode", "category", "questions", "current", "answers", "start_time", "timer_limit"]:
                del st.session_state[k]
        st.stop()
    else:
        i = st.session_state.current
        q = st.session_state.questions[i]
        st.markdown(f"⏳ Time Left: {remaining} sec")
        with st.form(f"form_time_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            choices = q["options"].copy()
            random.shuffle(choices)
            picked = st.radio("Choose your answer:", choices)
            submitted = st.form_submit_button("Submit")
        if submitted:
            correct = picked.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.info(f"💡 {q['explanation']}")
            st.caption(f"📚 Source: {q['source']}")
            st.session_state.current += 1

# --- Leaderboard Display ---
st.markdown("---")
if st.checkbox("📊 Show Leaderboard"):
    leaderboard = load_leaderboard()
    if leaderboard:
        recent = sorted(leaderboard, key=lambda x: x["timestamp"], reverse=True)[:15]
        for r in recent:
            pct = round(r["score"] / r["total"] * 100) if r["total"] > 0 else 0
            st.markdown(f"- {r['timestamp']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} ({pct}%) in {r['duration']}s")
    else:
        st.info("No scores yet. Be the first to play!")

st.caption("© 2025 - AML Mastermind | Inspired by FATF, IOSCO, IMF & World Bank")
