import streamlit as st
import json
import random
import time

# --- Configuration ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"

# --- Utility Functions ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def show_question(q, idx):
    st.subheader(f"Q{idx+1}: {q['question']}")
    options = q["options"].copy()
    random.shuffle(options)
    return st.radio("Choose your answer:", options, key=f"answer_{idx}")

# --- App Start ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 AML Mastermind Deluxe")
    password = st.text_input("Enter the password to play:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.experimental_rerun()
    elif password != "":
        st.error("Incorrect password.")
    st.stop()

# --- Player Info ---
st.title("🕵️ AML Mastermind Deluxe")
player_name = st.text_input("Enter your name:")
if not player_name:
    st.warning("Please enter your name to start.")
    st.stop()

questions_data = load_questions()
grouped = {}
for q in questions_data:
    cat = q.get("category", "Other")
    grouped.setdefault(cat, []).append(q)

# --- Initialize session state ---
if "mode" not in st.session_state:
    st.session_state.mode = None
if "category" not in st.session_state:
    st.session_state.category = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current" not in st.session_state:
    st.session_state.current = 0
if "score" not in st.session_state:
    st.session_state.score = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = None

# --- Game Setup ---
if st.session_state.mode is None:
    mode = st.selectbox("🎮 Select Game Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("📚 Select Category", list(grouped.keys()))
    if mode == "Classic Quiz":
        num = st.slider("🔢 Number of Questions", 5, 30, 10)
    else:
        num = 999  # Time attack uses as many as possible
    if st.button("Start Game"):
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = random.sample(grouped[category], min(num, len(grouped[category])))
        st.session_state.current = 0
        st.session_state.score = 0
        if mode == "Time Attack":
            st.session_state.start_time = time.time()
        st.experimental_rerun()

# --- Classic Mode ---
elif st.session_state.mode == "Classic Quiz":
    idx = st.session_state.current
    if idx < len(st.session_state.questions):
        q = st.session_state.questions[idx]
        answer = show_question(q, idx)
        if st.button("Submit Answer"):
            if answer == q["correct_answer"]:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Wrong! Correct: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.experimental_rerun()
    else:
        total = len(st.session_state.questions)
        score = st.session_state.score
        st.markdown(f"### 🎯 Final Score: {score}/{total}")
        if score / total >= 0.75:
            st.success(f"🏆 Congratulations {player_name}! You passed and earned your certificate!")
        else:
            st.info("Try again to reach 75% to earn your certificate.")
        if st.button("Play Again"):
            for key in ["mode", "category", "questions", "current", "score"]:
                del st.session_state[key]
            st.experimental_rerun()

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
        st.markdown(f"⏳ Time Left: **{remaining} seconds**")
        idx = st.session_state.current
        q = st.session_state.questions[idx]
        answer = show_question(q, idx)
        if st.button("Submit Answer"):
            if answer == q["correct_answer"]:
                st.success("✅ Correct!")
                st.session_state.score += 1
            else:
                st.error(f"❌ Wrong! Correct: {q['correct_answer']}")
            st.caption(q["explanation"])
            st.session_state.current += 1
            st.experimental_rerun()

st.markdown("---")
st.caption("Built with ❤️ for AML training – FATF, IOSCO, IMF & World Bank inspired.")
