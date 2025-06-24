import streamlit as st
import json
import os
import random
import time
from datetime import datetime

QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- UTILS ---
def load_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json_file(filepath, entry):
    data = load_json_file(filepath)
    data.append(entry)
    save_json_file(filepath, data)

# --- SESSION INIT ---
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.current = 0
    st.session_state.feedback_displayed = False
    st.session_state.submitted = False

# --- PAGE: NAME ENTRY ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    name = st.text_input("Enter your name to begin:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# --- PAGE: INSTRUCTIONS + SETTINGS ---
elif st.session_state.page == "instructions":
    st.title("📋 Instructions")
    st.markdown("""
Welcome to the AML Mastermind Quiz!

- Choose game mode and topic
- Click Submit once: see feedback
- Click Submit again: go to next question

🔒 Disclaimer: This is for training only. It may include simplifications and is not legal advice.
""")
    st.session_state.mode = st.radio("Select Mode", ["Classic", "Time Attack"])
    all_qs = load_json_file(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "General") for q in all_qs))
    st.session_state.category = st.selectbox("Select Topic", categories)

    if st.session_state.mode == "Classic":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
        st.session_state.num_questions = 99

    if st.button("Start Quiz"):
        pool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.feedback_displayed = False

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    current = st.session_state.current
    questions = st.session_state.questions
    q = questions[current]

    if f"options_{current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{current}"] = opts

    st.markdown(f"**Q{current + 1}: {q['question']}**")
    options = st.session_state[f"options_{current}"]
    selected = st.radio("Choose your answer:", options, key=f"q_{current}")

    if st.button("Submit"):
        if not st.session_state.feedback_displayed:
            correct = q["correct_answer"]
            picked = selected.strip().lower()
            is_correct = picked == correct.strip().lower()
            st.session_state.answers.append(is_correct)
            st.session_state.feedback_displayed = True

            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {correct}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")

        else:
            st.session_state.current += 1
            st.session_state.feedback_displayed = False

            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.title("✅ Quiz Complete!")
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")

    if not st.session_state.submitted:
        entry = {
            "name": st.session_state.player_name[:5] + "###",
            "score": score,
            "duration": duration,
            "category": st.session_state.category,
            "timestamp": datetime.now().isoformat()
        }
        append_to_json_file(LEADERBOARD_FILE, entry)
        st.session_state.submitted = True

    # Leaderboard
    st.markdown("---\n## 🏆 Leaderboard")
    data = load_json_file(LEADERBOARD_FILE)
    top = sorted(data, key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, entry in enumerate(top, 1):
        st.markdown(f"{i}. **{entry.get('name', '???')}** | {entry.get('score', 0)} pts | {entry.get('duration', '?')}s | {entry.get('category', '?')}")

    # Feedback section
    st.markdown("---\n## 💬 Leave a private comment:")
    comment = st.text_area("Your comment:")
    if st.button("Submit Comment") and comment.strip():
        append_to_json_file(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thank you! Your comment has been saved.")

    # Admin section
    st.markdown("---\n## 🔐 Admin Access")
    pw = st.text_input("Enter admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted.")
        comments = load_json_file(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "name"
