import streamlit as st
import json
import random
import time
from datetime import datetime

# Load AML questions
with open("questions_cleaned.json", "r", encoding="utf-8") as f:
    all_questions = json.load(f)

crypto_questions = [q for q in all_questions if q["category"] == "Crypto"]
funds_questions = [q for q in all_questions if q["category"] == "Collective Investment Sector"]
banking_questions = [q for q in all_questions if q["category"] == "Banking"]

# --- Password Protection ---
PASSWORD = "iloveaml2025"
def check_password():
    def password_entered():
        if st.session_state["password"] == PASSWORD:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password to continue", type="password", on_change=password_entered, key="password")
        st.stop()
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password to continue", type="password", on_change=password_entered, key="password")
        st.error("❌ Incorrect password")
        st.stop()

check_password()

# --- Game Initialization ---
st.title("🧠 AML Mastermind Game")
st.markdown("Test your knowledge of AML/CFT in various financial sectors!")

if "step" not in st.session_state:
    st.session_state.step = "start"
    st.session_state.name = ""
    st.session_state.category = ""
    st.session_state.questions = []
    st.session_state.score = 0
    st.session_state.index = 0
    st.session_state.start_time = None
    st.session_state.total_questions = 10

# --- Step 1: Welcome Screen ---
if st.session_state.step == "start":
    st.session_state.name = st.text_input("Enter your name:")
    st.session_state.category = st.radio("Choose your category:", ["Crypto", "Collective Investment Sector", "Banking"])
    if st.button("Next"):
        st.session_state.step = "count"
        st.rerun()

# --- Step 2: Choose number of questions ---
elif st.session_state.step == "count":
    st.session_state.total_questions = st.radio("How many questions do you want?", [10, 20, 30])
    if st.button("Start Game"):
        pool = {
            "Crypto": crypto_questions,
            "Collective Investment Sector": funds_questions,
            "Banking": banking_questions
        }[st.session_state.category]
        st.session_state.questions = random.sample(pool, min(st.session_state.total_questions, len(pool)))
        st.session_state.score = 0
        st.session_state.index = 0
        st.session_state.start_time = time.time()
        st.session_state.step = "question"
        st.rerun()

# --- Step 3: Game Loop ---
elif st.session_state.step == "question":
    q = st.session_state.questions[st.session_state.index]
    index = st.session_state.index

    st.markdown(f"**Question {index + 1}/{st.session_state.total_questions}**")
    st.markdown(f"### {q['question']}")

    answered_key = f"answered_{index}"
    selected_key = f"selected_{index}"

    if answered_key not in st.session_state:
        st.session_state[answered_key] = False

    if not st.session_state[answered_key]:
        selected = st.radio("Choose your answer:", q["options"], key=selected_key)
        if st.button("Submit Answer"):
            st.session_state[answered_key] = True
            if selected == q["correct_answer"]:
                st.success("Correct! ✅")
                st.session_state.score += 1
            else:
                st.error(f"Wrong! ❌ The correct answer was: {q['correct_answer']}")
            st.info(f"💬 Explanation: {q['explanation']}\n\n🔗 Source: {q['source']}")
    else:
        st.success("Answer submitted.")
        st.info(f"💬 Explanation: {q['explanation']}\n\n🔗 Source: {q['source']}")
        if st.button("Next Question"):
            st.session_state.index += 1
            if st.session_state.index >= st.session_state.total_questions:
                st.session_state.step = "result"
            st.rerun()

# --- Step 4: Result ---
elif st.session_state.step == "result":
    score = st.session_state.score
    total = st.session_state.total_questions
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## 🎉 Game Over!")
    st.markdown(f"**Name:** {st.session_state.name}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if percent >= 75:
        st.success("🏅 Great job! You passed the AML challenge!")
    else:
        st.warning("📘 Keep learning and try again!")

    if st.button("Replay"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- Footer Disclaimer ---
st.markdown(
    "<hr style='margin-top: 50px;'><div style='text-align:center; font-size: 12px; color: grey;'>"
    "This is an educational AML training game. Developed by Guilhem ROS, 2025."
    "</div>",
    unsafe_allow_html=True
)
