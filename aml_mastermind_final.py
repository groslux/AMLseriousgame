import streamlit as st
import json
import random
import time
from datetime import datetime

# Load questions
@st.cache_data
def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# Initialize session state
def init_state():
    defaults = {
        "page": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "submitted_answer": False,
        "selected_answer": None,
        "score": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)

# Name input page
if st.session_state.page == "name":
    st.title("AML Serious Game")
    st.session_state.player_name = st.text_input("Enter your name:")
    if st.session_state.player_name:
        if st.button("Continue"):
            st.session_state.page = "instructions"
            st.rerun()
    st.stop()

# Instructions page
if st.session_state.page == "instructions":
    st.title("🕵️ Instructions")
    st.markdown("""
Welcome to the AML Quiz!

- You'll be asked a series of questions.
- Choose the correct answer and click **Submit**.
- After seeing feedback, click **Next** to proceed.

🔒 **Disclaimer**: Educational only. May contain simplifications or errors. Not legal advice.
""")
    if st.button("Start Quiz"):
        category = random.choice(list(grouped.keys()))
        questions = grouped[category]
        random.shuffle(questions)
        st.session_state.questions = questions[:5]
        st.session_state.category = category
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.rerun()
    st.stop()

# Quiz page
if st.session_state.page == "quiz":
    idx = st.session_state["current"]
    questions = st.session_state.questions

    if idx >= len(questions):
        st.session_state.page = "results"
        st.rerun()
        st.stop()

    q = questions[idx]
    st.markdown(f"**Question {idx+1} of {len(questions)}**")
    st.markdown(q["question"])

    if f"options_{idx}" not in st.session_state:
        options = q["options"].copy()
        random.shuffle(options)
        st.session_state[f"options_{idx}"] = options

    options = st.session_state[f"options_{idx}"]
    selected = st.radio("Your answer:", options, index=0, key=f"selected_{idx}")

    if not st.session_state.submitted_answer:
        if st.button("Submit"):
            st.session_state.selected_answer = selected
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.session_state.score += int(is_correct)
            st.session_state.submitted_answer = True
            st.rerun()
        st.stop()
    else:
        correct = q["correct_answer"]
        picked = st.session_state.selected_answer
        is_correct = picked.strip().lower() == correct.strip().lower()
        st.success("✅ Correct!" if is_correct else f"❌ Wrong! Correct: {correct}")
        st.info(q.get("explanation", "No explanation provided."))
        st.caption(f"Source: {q.get('source', 'Unknown')}")
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.submitted_answer = False
            st.session_state.selected_answer = None
            st.rerun()
        st.stop()

# Results page
if st.session_state.page == "results":
    duration = int(time.time() - st.session_state.start_time)
    total = len(st.session_state.questions)
    score = st.session_state.score
    percent = round(score / total * 100)

    st.title("🏁 Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
