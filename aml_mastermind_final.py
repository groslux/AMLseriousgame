import streamlit as st
import json
import random
import time
from datetime import datetime
import os

# --- CONFIGURATION ---
DATA_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = "leaderboard.json"
TIME_OPTIONS = [60, 120, 180]

# --- SETUP ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- LOAD DATA ---
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

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_leaderboard(records):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

# --- INITIAL STATE ---
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
    "game_ended": False
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- LOAD QUESTIONS ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- UI: GAME TITLE ---
st.title("🕵️ AML Mastermind Deluxe")

# --- UI: NAME INPUT ---
st.session_state.player_name = st.text_input("Enter your name to begin:")

if not st.session_state.player_name.strip():
    st.stop()

# --- UI: SETUP BEFORE GAME STARTS ---
if not st.session_state["game_started"]:
    st.subheader("🎮 Choose your game mode")
    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Category", list(grouped.keys()))

    if mode == "Classic Quiz":
        num_questions = st.slider("How many questions?", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped.get(category, [])
        if not pool:
            st.error("No questions found in selected category.")
            st.stop()

        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.start_time = time.time()
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.game_started = True
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.game_ended = False
    else:
        st.stop()

# --- GAME LOOP ---
if not st.session_state.game_ended and st.session_state.current < len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.current]

    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.game_ended = True
        else:
            st.markdown(f"⏳ Time Left: **{remaining} seconds**")

    if not st.session_state.game_ended:
        st.markdown(f"### Question {st.session_state.current + 1}: {q['question']}")
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"q{st.session_state.current}")

        if st.button("Submit Answer", key=f"submit_{st.session_state.current}"):
            correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong. Correct: **{q['correct_answer']}**")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
            st.session_state.current += 1
else:
    st.session_state.game_ended = True

# --- RESULTS ---
if st.session_state.game_ended:
    score = sum(st.session_state.answers)
    total = st.session_state.current
    pct = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## 🧾 Game Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({pct}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if pct >= 75:
        st.success("🏅 Well done! Certificate earned!")
    else:
        st.info("💡 Keep practicing to master AML!")

    leaderboard = load_leaderboard()
    leaderboard.append({
        "name": st.session_state.player_name.strip()[:3] + "###",
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "score": score,
        "total": total,
        "percent": pct,
        "duration": duration,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_leaderboard(leaderboard)

    if st.checkbox("📊 Show Leaderboard"):
        sorted_lb = sorted(leaderboard, key=lambda x: (-x["percent"], x["duration"]))
        for r in sorted_lb[:10]:
            st.markdown(
                f"- {r['timestamp']} | {r['name']} | {r['mode']} | {r['category']} | "
                f"{r['score']}/{r['total']} ({r['percent']}%) in {r['duration']}s"
            )

    if st.button("Play Again"):
        for k in defaults:
            st.session_state.pop(k, None)

# --- FOOTER ---
st.markdown("---")
st.caption("Made for AML training – Powered by FATF, IOSCO, IMF & World Bank best practices.")
