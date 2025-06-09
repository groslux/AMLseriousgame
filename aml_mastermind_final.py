import streamlit as st
import json
import random
import time
from datetime import datetime

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
        cat = q.get("category", "Other").strip()
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
    if password:
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop()

# --- Load & group questions ---
questions_data = load_questions()
grouped = group_questions_by_category(questions_data)

# --- Session Initialization ---
for key, default in {
    "mode": None, "category": None, "questions": [],
    "current": 0, "answers": [], "start_time": None,
    "player_name": "", "max_time": 0, "name_confirmed": False
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- Player Name Step ---
if not st.session_state.name_confirmed:
    st.title("🕵️ Welcome to AML Mastermind Deluxe")
    st.session_state.player_name = st.text_input("Enter your name:")
    if st.button("Confirm Name") and st.session_state.player_name.strip() != "":
        st.session_state.name_confirmed = True
        st.rerun()
    st.stop()

# --- Game Setup ---
if st.session_state.mode is None:
    st.title("🎮 Select Game Mode")
    st.session_state.mode = st.radio("Choose a game mode:", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Select a category:", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        st.session_state.max_time = st.radio("Time Limit (in seconds):", [60, 120, 180])

    if st.button("Start Game"):
        qlist = grouped.get(st.session_state.category, [])
        if not qlist:
            st.error("❌ No questions found for this category.")
            st.stop()

        if st.session_state.mode == "Classic Quiz":
            st.session_state.questions = random.sample(qlist, min(st.session_state.num_questions, len(qlist)))
        else:
            random.shuffle(qlist)
            st.session_state.questions = qlist
            st.session_state.start_time = time.time()

        st.session_state.current = 0
        st.session_state.answers = []
        st.rerun()

# --- Classic Quiz Mode ---
if st.session_state.mode == "Classic Quiz" and st.session_state.current < len(st.session_state.questions):
    i = st.session_state.current
    q = st.session_state.questions[i]
    st.markdown(f"### Question {i + 1}/{len(st.session_state.questions)}")
    with st.form(key=f"form_classic_{i}"):
        st.subheader(q["question"])
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"answer_{i}")
        submit = st.form_submit_button("Submit Answer")

    if submit:
        correct = selected.strip().lower() == q["correct_answer"].strip().lower()
        st.session_state.answers.append(correct)
        if correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
        st.caption(q["explanation"])
        st.session_state.current += 1
        st.rerun()

# --- Classic Mode Result ---
if st.session_state.mode == "Classic Quiz" and st.session_state.current >= len(st.session_state.questions):
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    st.success(f"🏁 You completed the quiz, {st.session_state.player_name}!")
    if total > 0:
        percent = round(score / total * 100)
        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%)")
        if percent >= 75:
            st.success("🏅 Congratulations! You earned a certificate!")
        else:
            st.info("📘 Keep learning and try again!")
    else:
        st.warning("⚠️ No valid questions were loaded.")

    if st.button("Play Again"):
        for k in ["mode", "category", "questions", "current", "answers", "start_time", "max_time"]:
            del st.session_state[k]
        st.rerun()

# --- Time Attack Mode ---
if st.session_state.mode == "Time Attack":
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = st.session_state.max_time - elapsed
    if remaining <= 0 or st.session_state.current >= len(st.session_state.questions):
        score = sum(st.session_state.answers)
        st.success(f"⏱️ Time's up, {st.session_state.player_name}!")
        st.markdown(f"### 🧮 Score: {score} correct answers in {st.session_state.max_time} seconds")
        if score >= 10:
            st.success("🏅 Congratulations! You earned a certificate!")
        else:
            st.info("📘 Keep practicing to improve your score!")

        if st.button("Play Again"):
            for k in ["mode", "category", "questions", "current", "answers", "start_time", "max_time"]:
                del st.session_state[k]
            st.rerun()
        st.stop()

    i = st.session_state.current
    q = st.session_state.questions[i]
    st.markdown(f"⏳ Time Remaining: **{remaining} seconds**")
    st.markdown(f"### Question {i + 1}")
    with st.form(key=f"form_ta_{i}"):
        st.subheader(q["question"])
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Choose your answer:", options, key=f"ta_answer_{i}")
        submit = st.form_submit_button("Submit Answer")

    if submit:
        correct = selected.strip().lower() == q["correct_answer"].strip().lower()
        st.session_state.answers.append(correct)
        if correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
        st.caption(q["explanation"])
        st.session_state.current += 1
        st.rerun()

# --- Footer ---
st.markdown("---")
st.caption("📚 Powered by FATF, IOSCO & IMF guidelines – Created by Guilhem ROS, 2025")
