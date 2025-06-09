import streamlit as st
import json
import random
import time
from datetime import datetime

# --- Config ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- UI Setup ---
st.set_page_config(page_title="AML Mastermind", layout="centered")

# --- Authentication ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    st.title("🔐 AML Mastermind Deluxe")
    pw = st.text_input("Enter password to continue:", type="password")
    if pw == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    elif pw:
        st.error("Wrong password.")
    st.stop()

# --- Load and Prepare Data ---
questions_data = load_questions()
categories = group_by_category(questions_data)

# --- Session Defaults ---
defaults = {
    "step": "intro",
    "player_name": "",
    "mode": None,
    "category": None,
    "questions": [],
    "answers": [],
    "current": 0,
    "start_time": None,
    "max_time": 0,
    "done": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Step: Introduction ---
if st.session_state.step == "intro":
    st.title("🎯 AML Mastermind Deluxe")
    name = st.text_input("Enter your name to start:", value=st.session_state.player_name)
    if st.button("Confirm Name") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.step = "mode"
        st.rerun()
    st.stop()

# --- Step: Select Mode & Category ---
if st.session_state.step == "mode":
    st.title("🎮 Game Setup")
    st.session_state.mode = st.radio("Choose your mode:", ["Classic Quiz", "Time Attack"], index=0)
    st.session_state.category = st.selectbox("Select a category:", list(categories.keys()))
    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of questions", 5, 30, 10)
    else:
        st.session_state.max_time = st.radio("Time limit (seconds):", [60, 120, 180], index=1)

    if st.button("Start Game"):
        all_q = categories.get(st.session_state.category, [])
        if not all_q:
            st.error("❌ No questions found in this category.")
            st.stop()
        random.shuffle(all_q)
        st.session_state.questions = (
            all_q[:st.session_state.num_questions] if st.session_state.mode == "Classic Quiz" else all_q
        )
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.done = False
        st.session_state.start_time = time.time() if st.session_state.mode == "Time Attack" else None
        st.session_state.step = "quiz"
        st.rerun()
    st.stop()

# --- Step: Quiz ---
if st.session_state.step == "quiz":
    questions = st.session_state.questions
    index = st.session_state.current
    mode = st.session_state.mode

    if mode == "Time Attack":
        elapsed = int(time.time() - st.session_state.start_time)
        time_left = st.session_state.max_time - elapsed
        if time_left <= 0 or index >= len(questions):
            st.session_state.done = True
            st.session_state.step = "result"
            st.rerun()
        st.markdown(f"⏳ Time left: **{time_left} seconds**")

    if index < len(questions):
        q = questions[index]
        st.markdown(f"### Q{index + 1}: {q['question']}")

        answer_key = f"answer_{index}"
        submitted_key = f"submitted_{index}"

        if submitted_key not in st.session_state:
            with st.form(key=f"form_{index}"):
             random.seed(q["id"])  # deterministic shuffle based on question ID
                opts = q["options"].copy()
                random.shuffle(opts)
                sel = st.radio("Choose an answer:", opts, key=answer_key)
                submit = st.form_submit_button("Submit")

            if submit:
                st.session_state[submitted_key] = True
                selected_clean = sel.strip().lower()
                correct_clean = q["correct_answer"].strip().lower()
                correct = selected_clean == correct_clean
                st.session_state.answers.append(correct)
                st.session_state[f"was_correct_{index}"] = correct
                st.session_state[f"selected_{index}"] = sel
                st.rerun()
        else:
            correct = st.session_state[f"was_correct_{index}"]
            sel = st.session_state[f"selected_{index}"]

            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! You chose: {sel}\n\nCorrect answer: {q['correct_answer']}")

            if "explanation" in q:
                st.markdown(f"**Explanation:** {q['explanation']}")
            if "source" in q:
                st.markdown(f"🔗 **Source:** {q['source']}")

            if st.button("Next"):
                st.session_state.current += 1
                if mode == "Classic Quiz" and st.session_state.current >= len(questions):
                    st.session_state.done = True
                    st.session_state.step = "result"
                st.rerun()
    else:
        st.session_state.done = True
        st.session_state.step = "result"
        st.rerun()

# --- Step: Result ---
if st.session_state.step == "result":
    st.title("✅ Quiz Completed")
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    if total > 0:
        percent = round(score / total * 100)
        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%)")
        if percent >= 75:
            st.success("🏅 Certificate earned!")
        else:
            st.info("📘 Try again to improve your score.")
    else:
        st.warning("⚠️ No questions were answered.")

    if st.button("Play Again"):
        for k in defaults.keys():
            del st.session_state[k]
        st.rerun()

# --- Footer ---
st.markdown("---")
st.caption("© 2025 – AML Mastermind. Powered by FATF / IOSCO / IMF best practices.")
