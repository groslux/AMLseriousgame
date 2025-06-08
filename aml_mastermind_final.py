import streamlit as st
import json
import random
import time

# --- Configuration ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_questions_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other")
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- Streamlit Setup ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- Auth ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 AML Mastermind Deluxe")
    password = st.text_input("Enter the password to play:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_rerun()
    elif password:
        st.error("Incorrect password.")
    st.stop()

# --- Player name ---
st.title("🕵️ AML Mastermind Deluxe")
player_name = st.text_input("Enter your name:")
if not player_name:
    st.warning("Please enter your name to start.")
    st.stop()

# --- Load & group questions ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- Session Initialization ---
for key, default in {
    "mode": None, "category": None, "questions": [],
    "current": 0, "score": 0, "start_time": None, "trigger_next": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Game Selection ---
if st.session_state.mode is None:
    st.subheader("🎮 Choose your game mode")
    st.session_state.mode = st.selectbox("Game Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Category", list(grouped.keys()))
    question_count = 30 if st.session_state.mode == "Classic Quiz" else 999
    if st.session_state.mode == "Classic Quiz":
        question_count = st.slider("Number of Questions", 5, 30, 10)

    if st.button("Start Game"):
        st.session_state.questions = random.sample(
            grouped[st.session_state.category],
            min(question_count, len(grouped[st.session_state.category]))
        )
        st.session_state.current = 0
        st.session_state.score = 0
        if st.session_state.mode == "Time Attack":
            st.session_state.start_time = time.time()
        st.experimental_rerun()

# --- Classic Quiz Mode ---
elif st.session_state.mode == "Classic Quiz":
    i = st.session_state.current
    if i < len(st.session_state.questions):
        q = st.session_state.questions[i]
        with st.form(key=f"form_classic_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            options = q["options"].copy()
            random.shuffle(options)
            selected = st.radio("Choose your answer:", options, key=f"answer_{i}")
            submit = st.form_submit_button("Submit Answer")

        if submit:
            if selected == q["correct_answer"]:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.session_state.trigger_next = True

# --- Time Attack Mode ---
elif st.session_state.mode == "Time Attack":
    now = time.time()
    remaining = 120 - int(now - st.session_state.start_time)
    if remaining <= 0 or st.session_state.current >= len(st.session_state.questions):
        st.markdown(f"### ⌛ Time's up! Score: {st.session_state.score}")
        if st.session_state.score >= 10:
            st.success(f"🏆 Well done {player_name}, you earned your certificate!")
        else:
            st.info("Keep practicing to improve your score!")
        if st.button("Play Again"):
            for key in ["mode", "category", "questions", "current", "score", "start_time"]:
                del st.session_state[key]
            st.experimental_rerun()
    else:
        i = st.session_state.current
        q = st.session_state.questions[i]
        st.markdown(f"⏳ Time Left: **{remaining} seconds**")
        with st.form(key=f"form_time_{i}"):
            st.subheader(f"Q{i+1}: {q['question']}")
            options = q["options"].copy()
            random.shuffle(options)
            selected = st.radio("Choose your answer:", options, key=f"answer_{i}")
            submit = st.form_submit_button("Submit Answer")

        if submit:
            if selected == q["correct_answer"]:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.session_state.trigger_next = True

# --- Result Page (Classic Mode End) ---
if st.session_state.mode == "Classic Quiz" and st.session_state.current >= len(st.session_state.questions):
    total = len(st.session_state.questions)
    score = st.session_state.score
    st.markdown(f"### 🎯 Final Score: {score}/{total}")
    if total > 0 and score / total >= 0.75:
        st.success(f"🏆 Congratulations {player_name}, you passed and earned your certificate!")
    elif total > 0:
        st.info("Try again to reach 75% to earn your certificate.")
    else:
        st.warning("No questions were loaded. Please restart and select a different category.")
    if st.button("Play Again"):
        for key in ["mode", "category", "questions", "current", "score"]:
            del st.session_state[key]
        st.experimental_rerun()

# --- Controlled rerun ---
if st.session_state.get("trigger_next", False):
    st.session_state.trigger_next = False
    st.experimental_rerun()

# --- Footer ---
st.markdown("---")
st.caption("Built with ❤️ for AML training – FATF, IOSCO, IMF & World Bank inspired.")
