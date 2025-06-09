import streamlit as st
import json
import random
import time
from datetime import datetime

# --- Config ---
PASSWORD = "iloveaml2025"
DATA_FILE = "questions_cleaned.json"

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

# --- Auth ---
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

# --- Load questions ---
questions_data = load_questions()
categories = group_by_category(questions_data)

# --- Game States ---
default_state = {
    "player_name": "",
    "confirmed_name": False,
    "mode": None,
    "category": None,
    "questions": [],
    "answers": [],
    "current": 0,
    "start_time": None,
    "max_time": 0,
    "done": False
}
for key, val in default_state.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- Player name ---
if not st.session_state["confirmed_name"]:
    st.title("🎯 AML Mastermind Deluxe")
    st.session_state["player_name"] = st.text_input("Enter your name to start:")
    if st.button("Confirm") and st.session_state["player_name"].strip():
        st.session_state["confirmed_name"] = True
        st.rerun()
    st.stop()

# --- Game setup ---
if not st.session_state["mode"]:
    st.title("🎮 Game Setup")
    st.session_state["mode"] = st.radio("Choose your mode:", ["Classic Quiz", "Time Attack"])
    st.session_state["category"] = st.selectbox("Select a category:", list(categories.keys()))
    if st.session_state["mode"] == "Classic Quiz":
        st.session_state["num_questions"] = st.slider("Number of questions", 5, 30, 10)
    else:
        st.session_state["max_time"] = st.radio("Time limit (seconds):", [60, 120, 180])

    if st.button("Start Game"):
        all_q = categories.get(st.session_state["category"], [])
        if not all_q:
            st.error("❌ No questions in this category.")
            st.stop()
        random.shuffle(all_q)
        if st.session_state["mode"] == "Classic Quiz":
            st.session_state["questions"] = all_q[:st.session_state["num_questions"]]
        else:
            st.session_state["questions"] = all_q
            st.session_state["start_time"] = time.time()
        st.rerun()

# --- Quiz Loop ---
questions = st.session_state["questions"]
index = st.session_state["current"]
mode = st.session_state["mode"]
player = st.session_state["player_name"]

if st.session_state["done"]:
    score = sum(st.session_state["answers"])
    total = len(st.session_state["answers"])
    st.success(f"Game finished, {player}!")
    if total:
        percent = round(score / total * 100)
        st.markdown(f"### 🧮 Score: {score}/{total} ({percent}%)")
        if percent >= 75:
            st.success("🏅 Certificate earned!")
        else:
            st.info("📘 Try again to improve your score.")
    else:
        st.warning("⚠️ No questions answered.")

    if st.button("Play Again"):
        for k in list(default_state.keys()):
            st.session_state[k] = default_state[k]
        st.rerun()
    st.stop()

# --- Time check for Time Attack ---
if mode == "Time Attack":
    elapsed = int(time.time() - st.session_state["start_time"])
    time_left = st.session_state["max_time"] - elapsed
    if time_left <= 0 or index >= len(questions):
        st.session_state["done"] = True
        st.rerun()
    st.markdown(f"⏳ Time left: **{time_left} sec**")

# --- Show Question ---
if index < len(questions):
    q = questions[index]
    st.markdown(f"### Q{index + 1}: {q['question']}")
    with st.form(f"form_{index}"):
        opts = q["options"].copy()
        random.shuffle(opts)
        sel = st.radio("Choose an answer:", opts, key=f"answer_{index}")
        submitted = st.form_submit_button("Submit")

    if submitted:
        correct = sel.strip().lower() == q["correct_answer"].strip().lower()
        st.session_state["answers"].append(correct)
        if correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Wrong! Correct answer: {q['correct_answer']}")
        st.caption(q["explanation"])
        st.session_state["current"] += 1

        if mode == "Classic Quiz" and st.session_state["current"] >= len(questions):
            st.session_state["done"] = True
        st.rerun()

# --- Footer ---
st.markdown("---")
st.caption("© 2025 – AML Mastermind. Inspired by FATF, IOSCO, IMF guidelines.")
