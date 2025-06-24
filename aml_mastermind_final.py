import streamlit as st
import json
import random
import time
import os
from datetime import datetime

QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

st.set_page_config("AML Mastermind")

if "page" not in st.session_state:
    st.session_state.page = "intro"

# Page 1 – INTRO
if st.session_state.page == "intro":
    st.title("🧠 AML Mastermind")
    st.markdown("### 📋 Rules & Instructions")
    st.markdown("""
- Choose Classic or Time Attack mode  
- Select a topic  
- Submit your answers and learn from explanations  
- Certificate + Leaderboard + Feedback at the end
""")
    st.session_state.name = st.text_input("Enter your name:")
    mode = st.selectbox("Choose mode", ["Classic Quiz", "Time Attack"])
    questions = load_json(QUESTIONS_FILE)
    categories = sorted(set(q["category"] for q in questions))
    category = st.selectbox("Choose topic", categories)
    num_q = st.slider("Number of questions", 5, 20, 10) if mode == "Classic Quiz" else 99
    time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180]) if mode == "Time Attack" else None

    if st.button("Start Game") and st.session_state.name.strip():
        pool = [q for q in questions if q["category"] == category]
        random.shuffle(pool)
        st.session_state.questions = pool[:num_q]
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.time_limit = time_limit
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.feedback = False

# Page 2 – QUIZ
elif st.session_state.page == "quiz":
    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"### Q{st.session_state.current+1}: {q['question']}")
    if f"options_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{st.session_state.current}"] = opts
    options = st.session_state[f"options_{st.session_state.current}"]
    ans = st.radio("Choose:", options, key=f"q{st.session_state.current}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            is_correct = ans.strip().lower() == correct
            st.session_state.answers.append(is_correct)
            st.session_state.feedback = True
            st.success("✅ Correct!") if is_correct else st.error(f"❌ Wrong! Correct: {q['correct_answer']}")
            st.info(q.get("explanation", ""))
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.feedback = False
            if st.session_state.mode == "Time Attack":
                if time.time() - st.session_state.start_time > st.session_state.time_limit:
                    st.session_state.page = "results"
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# Page 3 – RESULTS
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time)
    st.markdown("## 🎉 Quiz Completed!")
    st.write(f"**Player:** {st.session_state.name}")
    st.write(f"**Score:** {score}/{total}")
    st.write(f"**Time:** {duration} sec")
    st.write(f"**Mode:** {st.session_state.mode} | **Topic:** {st.session_state.category}")
    leaderboard = load_json(LEADERBOARD_FILE)
    leaderboard.append({
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "time": duration,
        "mode": st.session_state.mode,
        "topic": st.session_state.category,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_json(LEADERBOARD_FILE, leaderboard)

    if st.checkbox("Show Leaderboard"):
        top = sorted(leaderboard, key=lambda x: (-x["score"], x["time"]))[:10]
        for i, entry in enumerate(top, 1):
            st.write(f"{i}. {entry['name']} | {entry['score']}/{entry['total']} | {entry['time']}s | {entry['mode']}")

    st.markdown("### 💬 Leave a comment (private):")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        comments = load_json(COMMENTS_FILE)
        comments.append({
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save_json(COMMENTS_FILE, comments)
        st.success("Thanks! Comment saved.")

    st.markdown("---")
    st.markdown("### 🔐 Admin Access to Comments")
    pw = st.text_input("Password:", type="password")
    if pw == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c['name']}** ({c.get('time', 'Unknown')}):")
            st.write(c["comment"])
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), file_name="comments.json")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
