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
    answer = st.radio("Choose your answer:", options, key=f"q_{idx}")
    return answer

# --- App Start ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 AML Mastermind Deluxe")
    password = st.text_input("Enter the password to play:", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
    elif password != "":
        st.error("Incorrect password.")
        st.stop()
    else:
        st.stop()

st.title("🕵️ AML Mastermind Deluxe")
st.markdown("Prove your anti-money laundering knowledge!")

player_name = st.text_input("Enter your name:")
if not player_name:
    st.warning("Please enter your name to start.")
    st.stop()

# Load and group questions by category
questions_data = load_questions()
grouped = {}
for q in questions_data:
    cat = q.get("category", "Other")
    grouped.setdefault(cat, []).append(q)

# UI: Select game mode and category
mode = st.selectbox("🎮 Select Game Mode", ["Classic Quiz", "Time Attack"])
category = st.selectbox("📚 Select Category", list(grouped.keys()))

if mode == "Classic Quiz":
    num_questions = st.slider("🔢 Number of Questions", 5, 30, 10)
    if st.button("Start Classic Quiz"):
        score = 0
        questions = random.sample(grouped[category], min(num_questions, len(grouped[category])))
        for i, q in enumerate(questions):
            answer = show_question(q, i)
            if st.button(f"Check Answer {i+1}", key=f"btn_{i}"):
                if answer == q["correct_answer"]:
                    st.success("✅ Correct!")
                    score += 1
                else:
                    st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
                st.caption(q["explanation"])

        st.markdown(f"### 🎯 Final Score: {score}/{num_questions}")
        if score / num_questions >= 0.75:
            st.success(f"🏆 Congratulations {player_name}, you passed and earned your certificate!")
        else:
            st.info("Try again to score at least 75% and earn your certificate.")

elif mode == "Time Attack":
    st.markdown("⏱️ You have **120 seconds** to answer as many questions as you can.")
    if st.button("Start Time Attack"):
        score = 0
        questions = random.sample(grouped[category], len(grouped[category]))
        start_time = time.time()
        i = 0
        while time.time() - start_time < 120 and i < len(questions):
            remaining = 120 - int(time.time() - start_time)
            st.markdown(f"⏳ Time Left: **{remaining} seconds**")
            q = questions[i]
            answer = show_question(q, i)
            if st.button(f"Submit Answer {i+1}", key=f"submit_{i}"):
                if answer == q["correct_answer"]:
                    st.success("✅ Correct!")
                    score += 1
                else:
                    st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
                st.caption(q["explanation"])
                i += 1
                time.sleep(1)
        st.markdown(f"### ⌛ Time's up! Your score: {score}")
        if score >= 10:
            st.success(f"🏆 Well done {player_name}! You earned your certificate!")
        else:
            st.info("Keep practicing to improve your score!")

st.markdown("---")
st.caption("Built with ❤️ for AML training – FATF, IOSCO, IMF & World Bank inspired.")
