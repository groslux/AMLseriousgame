import streamlit as st
import json
import os
import time
import random
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pathlib

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
PASSWORD_ADMIN = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- STATE INIT ---
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
        "submitted": False,
        "game_ended": False,
        "leaderboard_saved": False,
        "show_feedback": False,
        "admin_logged_in": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# --- UTILS ---
def load_leaderboard():
    if not os.path.exists(LEADERBOARD_PATH):
        return []
    with open(LEADERBOARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_leaderboard(data):
    os.makedirs(pathlib.Path(LEADERBOARD_PATH).parent, exist_ok=True)
    with open(LEADERBOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_leaderboard(record):
    lb = load_leaderboard()
    lb.append(record)
    save_leaderboard(lb)

def load_comments():
    if not os.path.exists(COMMENTS_PATH):
        return []
    with open(COMMENTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_comments(data):
    os.makedirs(pathlib.Path(COMMENTS_PATH).parent, exist_ok=True)
    with open(COMMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_comment(comment):
    comments = load_comments()
    comments.append(comment)
    save_comments(comments)

def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏅 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Excellent performance!")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica-Bold", 10)
            for line in [
                f"Q: {q.get('question')}",
                f"✔ Correct: {q.get('correct_answer')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation')}"
            ]:
                for subline in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(110, y, subline)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

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

questions_data = load_questions()
grouped = group_by_category(questions_data)

# --- PAGE 1: NAME ---
if st.session_state.page == "name":
    st.title("AML Serious Game for Supervisors")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>🧑‍💼 Players who played: <b>{len(load_leaderboard())}</b></div>", unsafe_allow_html=True)
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue ➡️") and st.session_state.player_name.strip():
        st.session_state.page = "intro"

# --- PAGE 2: INTRO ---
elif st.session_state.page == "intro":
    st.title("🔍 Welcome to the AML Serious Game")
    st.markdown("""
**🚨 Your Mission:**  
Test your AML supervision skills across Banking, Crypto, and Investment Funds.

📜 Earn your certificate  
🏆 Join the leaderboard  
✉️ Leave private feedback for the game creator

### 📝 Disclaimer:
This game is for educational and training purposes only. There may be mistakes or simplifications. This is not legal advice.

### How the Game Works:
- Choose Classic or Time Attack mode  
- Select a topic  
- Submit answers and learn from explanations
""")
    mode = st.selectbox("Choose game mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Select a topic", list(grouped.keys()))
    if mode == "Classic Quiz":
        num_q = st.slider("Number of questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game ▶️"):
        pool = grouped.get(category, [])
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_q] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# --- PAGE 3: QUIZ ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        st.markdown(f"⏱️ Time Left: **{max(0, remaining)} seconds**")
        if remaining <= 0:
            st.session_state.page = "result"

    idx = st.session_state.current
    if idx < len(st.session_state.questions):
        q = st.session_state.questions[idx]
        st.markdown(f"### Question {idx+1}: {q['question']}")
        if f"options_{idx}" not in st.session_state:
            opts = q["options"].copy()
            random.shuffle(opts)
            st.session_state[f"options_{idx}"] = opts
        options = st.session_state[f"options_{idx}"]
        selected = st.radio("Choose:", options, key=f"answer_{idx}")

        if not st.session_state.submitted:
            if st.button("Submit Answer"):
                st.session_state.submitted = True
                correct = q["correct_answer"].strip().lower()
                picked = selected.strip().lower()
                st.session_state.answers.append(picked == correct)
                st.session_state.show_feedback = True

        if st.session_state.show_feedback:
            is_correct = st.session_state.answers[-1]
            st.success("✅ Correct!" if is_correct else f"❌ Incorrect. Correct: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
            if st.button("Next Question ⏭️"):
                st.session_state.current += 1
                st.session_state.submitted = False
                st.session_state.show_feedback = False
    else:
        st.session_state.page = "result"

# --- RESULTS ---
elif st.session_state.page == "result":
    st.title("🎉 Game Complete!")
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")

    if not st.session_state.leaderboard_saved and score > 0:
        append_to_leaderboard({
            "name": st.session_state.player_name.strip()[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.session_state.leaderboard_saved = True

    incorrect = [st.session_state.questions[i] for i, c in enumerate(st.session_state.answers) if not c]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("### 🏆 Leaderboard")
    top10 = sorted(load_leaderboard(), key=lambda x: (-x['score'], x['duration']))[:10]
    for i, r in enumerate(top10, 1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['category']}")

    st.markdown("### ✉️ Leave a comment for the creator")
    comment = st.text_area("Write your comment (only visible to the creator)")
    if st.button("Submit Comment"):
        if comment.strip():
            append_comment({
                "name": st.session_state.player_name,
                "comment": comment.strip(),
                "timestamp": datetime.now().isoformat()
            })
            st.success("Comment submitted!")

    st.markdown("### 🔁 Play Again?")
    if st.button("Restart"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

# --- ADMIN VIEW COMMENTS ---
with st.sidebar:
    st.markdown("🔐 Admin Section")
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("Enter admin password", type="password")
        if st.button("Login"):
            if pwd == PASSWORD_ADMIN:
                st.session_state.admin_logged_in = True
                st.success("Logged in.")
    else:
        st.markdown("### 💬 Comments Received")
        for c in load_comments():
            st.markdown(f"🧑 {c['name']} at {c['timestamp']}")
            st.info(c['comment'])
