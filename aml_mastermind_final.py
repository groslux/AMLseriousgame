import streamlit as st
import json
import random
import time
from datetime import datetime
import os

import streamlit as st
import json
import random
import time
from datetime import datetime

# --- Configuration ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- Password Step ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 AML Mastermind Deluxe")
    password = st.text_input("Enter password to continue:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
    elif password:
        st.error("❌ Incorrect password.")
    st.stop()

# --- Player Name Step ---
st.title("🕵️ AML Mastermind Deluxe")
if "player_name" not in st.session_state:
    st.session_state.player_name = ""

if "name_entered" not in st.session_state:
    st.session_state.name_entered = False

if not st.session_state.name_entered:
    name = st.text_input("Enter your name:")
    start_game = st.button("Start Game")
    if start_game:
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.name_entered = True
        else:
            st.warning("Please enter your name.")
    st.stop()

# ✅ At this point, password and name have been successfully entered.
# You can now continue with question loading, mode selection, etc.

st.success(f"Welcome, {st.session_state.player_name}! Let's begin your AML journey.")


# --- PLAYER SETUP + START BUTTON ---
st.title("🕵️ AML Mastermind Deluxe")

if "player_ready" not in st.session_state:
    st.session_state.player_ready = False

if not st.session_state.player_ready:
    st.session_state.player_name = st.text_input("Enter your name to begin:")

    if st.session_state.player_name.strip() and st.button("Start"):
        st.session_state.player_ready = True
        st.session_state.mode = None
    st.stop()

    st.subheader("🎮 Choose your game mode")
    st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Select a Category", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("How many questions?", 5, 30, 10)
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped.get(st.session_state.category, [])
        if not pool:
            st.error("❌ No questions found in this category.")
            st.stop()
        random.shuffle(pool)
        if st.session_state.mode == "Classic Quiz":
            st.session_state.questions = pool[:st.session_state.num_questions]
        else:
            st.session_state.questions = pool
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.game_ended = False

# --- GAME LOOP ---
if st.session_state.questions and not st.session_state.game_ended:
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0 or st.session_state.current >= len(st.session_state.questions):
            st.session_state.game_ended = True
        else:
            st.markdown(f"⏳ Time Left: **{remaining} seconds**")

    if not st.session_state.game_ended and st.session_state.current < len(st.session_state.questions):
        q = st.session_state.questions[st.session_state.current]
        st.markdown(f"### Question {st.session_state.current + 1}: {q['question']}")
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"q{st.session_state.current}")

        if st.button("Submit Answer", key=f"submit_{st.session_state.current}"):
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(is_correct)
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong. Correct answer: **{q['correct_answer']}**")
            st.info(f"ℹ️ {q.get('explanation', 'No explanation provided.')}")
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
            st.session_state.current += 1
    else:
        st.session_state.game_ended = True

# --- RESULTS ---
if st.session_state.game_ended:
    score = sum(st.session_state.answers)
    total = st.session_state.current
    pct = round(score / total * 100) if total > 0 else 0
    duration = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0

    st.markdown("## 🧾 Game Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({pct}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if pct >= 75:
        st.success("🏅 Congratulations! You earned a certificate!")
    else:
        st.info("📘 Keep practicing to improve your score!")

    # --- Save Leaderboard ---
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

    # --- Show Leaderboard Option ---
    if st.checkbox("📊 Show Leaderboard"):
        sorted_lb = sorted(leaderboard, key=lambda x: (-x["percent"], x["duration"]))
        for r in sorted_lb[:10]:
            st.markdown(f"- {r['timestamp']} | {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} ({r['percent']}%) in {r['duration']}s")

    if st.button("Play Again"):
        for k in list(defaults.keys()) + ["num_questions"]:
            st.session_state.pop(k, None)
   

# --- FOOTER ---
st.markdown("---")
st.caption("Made for AML training – Powered by FATF, IOSCO, IMF & World Bank best practices.")
