import streamlit as st
import json
import os
import random
import time
from datetime import datetime

# --- Constants ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- Helpers ---
def load_json(filepath, default=[]):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(filepath, entry):
    data = load_json(filepath)
    data.append(entry)
    save_json(filepath, data)

# --- Session state init ---
if "page" not in st.session_state:
    st.session_state.page = "start"
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "current" not in st.session_state:
    st.session_state.current = 0

# --- Page: Start ---
if st.session_state.page == "start":
    st.title("🕵️ AML Mastermind")
    st.markdown("### Enter your name to begin")
    name = st.text_input("Your name")
    if st.button("Start") and name.strip():
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            all_qs = json.load(f)
        st.session_state.name = name.strip()
        st.session_state.questions = random.sample(all_qs, 5)
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# --- Page: Quiz ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"### Question {st.session_state.current + 1}: {q['question']}")

    if f"options_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{st.session_state.current}"] = opts
    opts = st.session_state[f"options_{st.session_state.current}"]

    selected = st.radio("Your answer", opts, key=f"q_{st.session_state.current}")

    if not st.session_state.submitted:
        if st.button("Submit"):
            correct = q["correct_answer"]
            st.session_state["is_correct"] = selected == correct
            st.session_state.submitted = True
            if selected == correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {correct}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'N/A')}")
    else:
        if st.button("Next"):
            st.session_state.answers.append(st.session_state["is_correct"])
            st.session_state.current += 1
            st.session_state.submitted = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- Page: Results ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round((score / total) * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## ✅ Quiz Finished!")
    st.write(f"**Player:** {st.session_state.name}")
    st.write(f"**Score:** {score}/{total} ({percent}%)")
    st.write(f"**Duration:** {duration} seconds")

    # Save to leaderboard
    append_json(LEADERBOARD_FILE, {
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "timestamp": datetime.now().isoformat()
    })

    # Leaderboard display
    if st.checkbox("Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s")

    # Comment section
    st.markdown("### 🗣️ Leave a private comment")
    st.caption("Comments are only visible to the game creator.")
    feedback = st.text_area("Your comment")
    if st.button("Submit Comment") and feedback.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.name[:5] + "###",
            "comment": feedback.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you for your feedback!")

    # Admin
    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name', '???')}** ({c.get('time', '')}):")
                st.write(c.get("comment", ""))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json", "application/json")
        else:
            st.info("No comments yet.")

    # Play again
    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
