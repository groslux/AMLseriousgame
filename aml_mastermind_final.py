import streamlit as st
import json
import random
import time
from datetime import datetime
import os

# File paths
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"

# Ensure leaderboard file exists
os.makedirs(".streamlit", exist_ok=True)
if not os.path.exists(LEADERBOARD_FILE):
    with open(LEADERBOARD_FILE, "w") as f:
        json.dump([], f)

# Load questions
with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
    all_questions = json.load(f)

# --- INIT SESSION STATE ---
if "page" not in st.session_state:
    st.session_state.page = "start"
    st.session_state.current = 0
    st.session_state.answers = []
    st.session_state.feedback = False
    st.session_state.score = 0
    st.session_state.start_time = time.time()

# --- PING KEEPER ---
st.markdown("<small style='color:gray;'>Ping received ✅</small>", unsafe_allow_html=True)

# --- PAGE: START ---
if st.session_state.page == "start":
    st.title("🕵️ AML Mastermind")
    st.write("Enter your name to begin.")
    name = st.text_input("Your name")
    if name:
        st.session_state.name = name
        st.session_state.page = "quiz"
        random.shuffle(all_questions)
        st.session_state.questions = all_questions[:10]

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"**Question {st.session_state.current + 1}: {q['question']}**")

    if f"options_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{st.session_state.current}"] = opts

    options = st.session_state[f"options_{st.session_state.current}"]
    selected = st.radio("Choose an answer:", options, key=f"q_{st.session_state.current}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            correct = q["correct_answer"]
            if selected == correct:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Incorrect. Correct answer: {correct}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'No source')}")
            st.session_state.feedback = True
    else:
        if st.button("Submit"):
            st.session_state.current += 1
            st.session_state.feedback = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    duration = int(time.time() - st.session_state.start_time)
    score = st.session_state.score
    total = len(st.session_state.questions)
    percent = round(score / total * 100)

    st.markdown("## ✅ Quiz Complete!")
    st.write(f"**Name:** {st.session_state.name}")
    st.write(f"**Score:** {score}/{total} ({percent}%)")
    st.write(f"**Time:** {duration} seconds")

    with open(LEADERBOARD_FILE, "r") as f:
        leaderboard = json.load(f)

    leaderboard.append({
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "percent": percent,
        "duration": duration,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })

    with open(LEADERBOARD_FILE, "w") as f:
        json.dump(leaderboard, f, indent=2)

    st.markdown("### 🏆 Leaderboard")
    top = sorted(leaderboard, key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, entry in enumerate(top, 1):
        st.write(f"{i}. **{entry['name']}** | {entry['score']} pts | {entry['duration']}s")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()  # Optional for full restart — remove if strictly forbidden

