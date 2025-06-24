import streamlit as st
import json
import random
import time
import os
from datetime import datetime

# --- CONFIG ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- UTILS ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- INIT ---
st.set_page_config("AML Mastermind", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "intro"

# --- INTRO PAGE ---
if st.session_state.page == "intro":
    st.title("🧠 AML Mastermind")
    total_players = len(load_json(LEADERBOARD_FILE))
    st.markdown(f"👥 Players so far: **{total_players}**")
    st.markdown("## 👋 Enter your name to begin")
    st.session_state.name = st.text_input("Your name:")

    if st.session_state.name.strip():
        st.markdown("### 🧾 Choose your game settings")
        st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
        questions = load_json(QUESTIONS_FILE)
        categories = sorted(set(q["category"] for q in questions))
        st.session_state.category = st.selectbox("Topic", categories)
        if st.session_state.mode == "Classic Quiz":
            st.session_state.num_q = st.slider("How many questions?", 5, 20, 10)
            st.session_state.time_limit = None
        else:
            st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
            st.session_state.num_q = 99

        if st.button("🚀 Start Quiz"):
            pool = [q for q in questions if q["category"] == st.session_state.category]
            random.shuffle(pool)
            st.session_state.questions = pool[:st.session_state.num_q]
            st.session_state.current = 0
            st.session_state.answers = []
            st.session_state.start_time = time.time()
            st.session_state.feedback = False
            st.session_state.page = "quiz"

# --- QUIZ PAGE ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"### ❓ {q['question']}")
    if f"opts_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"opts_{st.session_state.current}"] = opts
    opts = st.session_state[f"opts_{st.session_state.current}"]
    selected = st.radio("Your answer:", opts, key=f"q{st.session_state.current}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(is_correct)
            st.session_state.feedback = True
            st.success("✅ Correct!") if is_correct else st.error(f"❌ Correct answer: {q['correct_answer']}")
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

# --- RESULTS PAGE ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time)
    st.title("✅ Quiz Complete!")
    st.write(f"**Player:** {st.session_state.name}")
    st.write(f"**Score:** {score}/{total}")
    st.write(f"**Time Taken:** {duration} sec")
    st.write(f"**Mode:** {st.session_state.mode} | **Topic:** {st.session_state.category}")

    # Save leaderboard
    lb = load_json(LEADERBOARD_FILE)
    lb.append({
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "time": duration,
        "mode": st.session_state.mode,
        "topic": st.session_state.category,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_json(LEADERBOARD_FILE, lb)

    # Show top 10
    if st.checkbox("📊 Show Leaderboard"):
        top = sorted(lb, key=lambda x: (-x["score"], x["time"]))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['time']}s | {r['mode']} | {r['topic']}")

    # Comment section
    st.markdown("### 💬 Leave feedback (only visible to admin)")
    comment = st.text_area("Your comment:")
    if st.button("Send Comment") and comment.strip():
        comments = load_json(COMMENTS_FILE)
        comments.append({
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        save_json(COMMENTS_FILE, comments)
        st.success("Thanks for your feedback!")

    st.caption("Comments are stored privately and not visible to other players.")

    # Admin view
    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("✅ Access granted")
        comments = load_json(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name', '???')}** ({c.get('time', 'Unknown')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    # Replay
    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
