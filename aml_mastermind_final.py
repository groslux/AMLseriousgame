import streamlit as st
import json
import random

# Set Streamlit page configuration
st.set_page_config(page_title="🧠 AML Mastermind", layout="centered")

# --- Load questions from JSON file ---
@st.cache_data
def load_questions():
    try:
        with open("questions_cleaned.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Failed to load questions: {e}")
        return []

# --- Group questions by category ---
def group_questions_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Uncategorized")
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(q)
    return grouped

# --- Initialization ---
questions_data = load_questions()
if not questions_data:
    st.stop()

grouped = group_questions_by_category(questions_data)

# --- Initialize session state ---
if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.category = list(grouped.keys())[0]
    st.session_state.questions = []
    st.session_state.score = 0

# --- Game UI ---
st.title("🧠 AML Mastermind")

# Step 0: Choose category
if st.session_state.step == 0:
    st.session_state.category = st.selectbox("Select a category", list(grouped.keys()))
    if st.button("Start Game"):
        selected_questions = grouped[st.session_state.category]
        if not selected_questions:
            st.error("No questions available for this category.")
            st.stop()
        st.session_state.questions = random.sample(
            selected_questions, k=min(10, len(selected_questions))
        )
        st.session_state.score = 0
        st.session_state.step = 1
        st.experimental_rerun()

# Steps 1 to N: Display questions
elif 1 <= st.session_state.step <= len(st.session_state.questions):
    q = st.session_state.questions[st.session_state.step - 1]
    st.markdown(f"**Question {st.session_state.step}**")
    st.markdown(q["question"])
    selected = st.radio("Choose one:", q["options"])

    if st.button("Submit Answer"):
        if selected == q["correct_answer"]:
            st.success("✅ Correct!")
            st.session_state.score += 1
        else:
            st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
        st.info(q["explanation"])
        st.session_state.step += 1
        st.button("Next", on_click=st.experimental_rerun)

# Final Step: Game Over
else:
    st.success(f"🎉 Game Over! Your score: {st.session_state.score} / {len(st.session_state.questions)}")
    if st.button("Play Again"):
        st.session_state.step = 0
        st.experimental_rerun()
