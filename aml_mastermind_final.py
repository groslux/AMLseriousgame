import streamlit as st
import json
import random
import time
from datetime import datetime

# --- Config ---
DATA_FILE = "questions_cleaned.json"

# --- Load Questions ---
@st.cache_data
def load_questions():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"❌ Failed to load questions: {e}")
        return []

def group_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- UI Setup ---
st.set_page_config(page_title="AML Mastermind", layout="centered")

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
    "done": False,
    "num_questions": 0
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Step: Introduction ---
if st.session_state.step == "intro":
    st.title("🎯 AML Mastermind Deluxe")
    name = st.text_input("Enter your name to start:", value=st.session_state.player_name)
    if st.button("Confirm Name"):
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.step = "mode"
        else:
            st.error("⚠️ Please enter a name.")
    st.stop()

# --- Step: Select Mode & Category ---
if st.session_state.step == "mode":
    st.title("🎮 Game Setup")
    st.session_state.mode = st.radio("Choose your mode:", ["Classic Quiz", "Time Attack"], index=0)
    st.session_state.category = st.selectbox("Select a category:", list(categories.keys()))
    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of questions", 5, 10, 20)
    else:
        st.session_state.max_time = st.radio("Time limit (seconds):", [60, 120, 180], index=1)

    if st.button("Start Game"):
        all_q = categories.get(st.session_state.category, [])
        if not all_q:
            st.error("❌ No questions found in this category.")
            st.stop()
        random.shuffle(all_q)
        if st.session_state.mode == "Classic Quiz":
            st.session_state.questions = all_q[:st.session_state.num_questions]
        else:
            st.session_state.questions = all_q
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.done = False
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"
   
    st.stop()

# --- Step: Quiz ---
if st.session_state.step == "quiz":
    questions = st.session_state.questions
    idx = st.session_state.current
    mode = st.session_state.mode

    if mode == "Time Attack":
        elapsed = int(time.time() - st.session_state.start_time)
        time_left = st.session_state.max_time - elapsed
        if time_left <= 0 or idx >= len(questions):
            st.session_state.done = True
            st.session_state.step = "result"
  
        st.markdown(f"⏳ Time left: **{time_left} seconds**")

    if idx < len(questions):
        q = questions[idx]
        st.markdown(f"### Q{idx + 1}: {q['question']}")
        st.progress((idx + 1) / len(questions))
        with st.form(key=f"form_{idx}"):
            opts = q["options"].copy()
            random.shuffle(opts)
            sel = st.radio("Choose an answer:", opts, key=f"answer_{idx}")
            submitted = st.form_submit_button("Submit")

        if submitted:
            correct = q["correct_answer"]
            is_correct = (sel.strip().casefold() == correct.strip().casefold())
            st.session_state.answers.append(is_correct)

            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong! Correct answer: **{correct}**")
            st.caption(f"**Explanation:** {q['explanation']}  \n🔗 **Source:** {q['source']}")

            st.session_state.current += 1
            time.sleep(0.3)
            if mode == "Classic Quiz" and st.session_state.current >= len(questions):
                st.session_state.done = True
                st.session_state.step = "result"
      
    else:
        st.session_state.done = True
        st.session_state.step = "result"
 

# --- Step: Result ---
if st.session_state.step == "result":
    st.title("✅ Quiz Completed")
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time)
    if total > 0:
        percent = round(score / total * 100)
        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%) in {duration} seconds")
        if percent >= 75:
            st.success(f"🏅 Certificate earned, {st.session_state.player_name}!")
        else:
            st.info("📘 Try again to improve your score.")
    else:
        st.warning("⚠️ No questions were answered.")

    if st.button("Play Again"):
        for k in list(defaults.keys()) + ["authenticated"]:
            st.session_state.pop(k, None)


# --- Footer ---
st.markdown("---")
st.caption("© 2025 – AML Mastermind. Powered by FATF / IOSCO / IMF best practices.")
