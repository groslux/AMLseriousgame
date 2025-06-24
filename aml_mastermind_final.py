import streamlit as st
import json
import os
import random
import time
from datetime import datetime

# ---------- CONFIG ----------
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
ADMIN_PASSWORD = "iloveaml2025"

# ---------- UTILS ----------
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

# ---------- INIT SESSION ----------
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.feedback_displayed = False
    st.session_state.current = 0

# ---------- PAGE 1: NAME ENTRY ----------
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    st.markdown("Welcome! Please enter your name to begin:")
    name = st.text_input("Your name")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# ---------- PAGE 2: INSTRUCTIONS ----------
elif st.session_state.page == "instructions":
    st.title("📋 Instructions")
    st.markdown("""
This quiz helps train AML investigators through quick questions.

- Choose Classic or Time Attack
- Select your topic
- Answer and learn with feedback!
- Earn a certificate and leaderboard spot

🔒 Disclaimer: This is a training tool. It may contain simplifications. Not legal advice.
    """)
    st.session_state.mode = st.radio("Select Mode", ["Classic", "Time Attack"])
    
    all_qs = load_json_file(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "General") for q in all_qs))
    st.session_state.category = st.selectbox("Choose a topic", categories)

    if st.session_state.mode == "Classic":
        st.session_state.num_questions = st.slider("How many questions?", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
        st.session_state.num_questions = 99

    if st.button("Start Quiz"):
        pool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.feedback_displayed = False

# ---------- PAGE 3: QUIZ ----------
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
            st.experimental_rerun()
        st.markdown(f"⏱️ Time left: {remaining}s")

    current = st.session_state.current
    q = st.session_state.questions[current]
    st.markdown(f"**Q{current + 1}: {q['question']}**")

    if f"options_{current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{current}"] = opts
    options = st.session_state[f"options_{current}"]

    selected = st.radio("Your answer:", options, key=f"answer_{current}")

    if not st.session_state.feedback_displayed:
        if st.button("Submit"):
            st.session_state.selected_answer = selected
            correct = q["correct_answer"]
            is_correct = selected.strip().lower() == correct.strip().lower()
            st.session_state.answers.append(is_correct)
            st.session_state.feedback_displayed = True

            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong. Correct answer: {correct}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'N/A')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.feedback_displayed = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# ---------- PAGE 4: RESULTS ----------
elif st.session_state.page == "results":
    st.title("🏁 Quiz Complete!")
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time)
    percent = round(score / total * 100)

    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration}s")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")

    # Store once per session
    if "submitted" not in st.session_state:
        leaderboard_entry = {
            "name": st.session_state.player_name[:5] + "###",
            "score": score,
            "duration": duration,
            "category": st.session_state.category,
            "timestamp": datetime.now().isoformat()
        }
        append_to_json_file(LEADERBOARD_FILE, leaderboard_entry)
        st.session_state.submitted = True

    # Leaderboard
    st.markdown("---\n## 🏆 Leaderboard (Top 10)")
    data = load_json_file(LEADERBOARD_FILE)
    top = sorted(data, key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, entry in enumerate(top, 1):
        st.markdown(f"{i}. **{entry.get('name', '???')}** | {entry.get('score', 0)} pts | {entry.get('duration', '?')}s | {entry.get('category', '?')}")

    # Feedback
    st.markdown("---\n## 💬 Feedback (private to creator)")
    comment = st.text_area("Your thoughts?")
    if st.button("Submit Comment") and comment.strip():
        append_to_json_file(".streamlit/comments.json", {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thanks! Your comment was submitted.")

    # Admin View
    st.markdown("---\n## 🔐 Admin Access")
    pw = st.text_input("Enter admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted.")
        comments = load_json_file(".streamlit/comments.json")
        for c in comments:
            st.markdown(f"**{c['name']}** ({c['time']}):")
            st.write(c['comment'])
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "name"
