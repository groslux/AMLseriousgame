import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os
import pathlib

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]
PASSWORD = "iloveaml2025"

# --- FILE UTILS ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- LEADERBOARD ---
def append_to_leaderboard(record):
    leaderboard = load_json(LEADERBOARD_PATH)
    leaderboard.append(record)
    save_json(LEADERBOARD_PATH, leaderboard)

def get_top_players():
    return sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]

def get_player_count():
    return len(load_json(LEADERBOARD_PATH))

# --- COMMENTS ---
def append_comment(record):
    comments = load_json(COMMENTS_PATH)
    comments.append(record)
    save_json(COMMENTS_PATH, comments)

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🎓 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.drawString(100, y, "👏 Excellent work! You're an AML star.")
    else:
        c.drawString(100, y, "📚 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]
            for line in lines:
                wrapped = [line[i:i+100] for i in range(0, len(line), 100)]
                for sub in wrapped:
                    c.drawString(110, y, sub)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGE SETUP ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

@st.cache_data
def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Other")
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- STATE ---
def init_state():
    defaults = {
        "step": "name",  # name -> intro -> quiz -> result
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "submitted": False,
        "score_saved": False,
        "comment_submitted": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)

# --- PAGE 1: NAME ---
if st.session_state.step == "name":
    st.title("AML Serious Game for Supervisors")
    st.markdown(f"👤 Already played: **{get_player_count()}** users")
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue"):
        if st.session_state.player_name.strip():
            st.session_state.step = "intro"
        else:
            st.warning("Please enter your name.")

# --- PAGE 2: INTRO ---
elif st.session_state.step == "intro":
    st.header("🕵️ Welcome to the AML Serious Game")
    st.markdown("""
**🚨 Your Mission:**  
Answer correctly and fast to climb the leaderboard!

💰 Topics: Crypto, Investment Funds, Banking  
📜 Certificate at the end  
🏆 Compete on the leaderboard  

**📝 Disclaimer**: This game is for educational purposes only. It may contain simplifications and is not legal advice.

""")
    st.subheader("Choose your mode and category")
    st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Category", list(grouped.keys()))
    if st.session_state.mode == "Classic Quiz":
        num = st.slider("Number of Questions", 5, 30, 10)
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped.get(st.session_state.category, [])
        random.shuffle(pool)
        st.session_state.questions = pool[:num] if st.session_state.mode == "Classic Quiz" else pool
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"

# --- PAGE 3: QUIZ ---
elif st.session_state.step == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.step = "result"
        else:
            st.markdown(f"⏱️ Time left: **{remaining} seconds**")

    idx = st.session_state.current
    if idx >= len(st.session_state.questions):
        st.session_state.step = "result"
    else:
        q = st.session_state.questions[idx]
        st.subheader(f"Question {idx + 1} of {len(st.session_state.questions)}")
        st.markdown(q["question"])

        if f"options_{idx}" not in st.session_state:
            opts = q["options"].copy()
            random.shuffle(opts)
            st.session_state[f"options_{idx}"] = opts

        selected = st.radio("Select an answer:", st.session_state[f"options_{idx}"], key=f"radio_{idx}")

        if not st.session_state.submitted:
            if st.button("Submit"):
                correct = q["correct_answer"].strip().lower()
                picked = selected.strip().lower()
                is_correct = picked == correct
                st.session_state.answers.append(is_correct)
                st.session_state.submitted = True
                if is_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
                st.info(q.get("explanation", "No explanation provided."))
                st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
        else:
            if st.button("Next"):
                st.session_state.current += 1
                st.session_state.submitted = False
                st.rerun()

# --- PAGE 4: RESULTS ---
elif st.session_state.step == "result":
    st.header("🎉 Quiz Complete!")
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")

    if not st.session_state.score_saved:
        append_to_leaderboard({
            "name": st.session_state.player_name[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.session_state.score_saved = True

    incorrect = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.subheader("🏆 Leaderboard (Top 10)")
    for i, r in enumerate(get_top_players(), 1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s")

    st.subheader("💬 Leave a comment for the game creator")
    comment = st.text_area("Your comment (only visible to the creator):")
    if st.button("Submit Comment"):
        append_comment({
            "name": st.session_state.player_name,
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Comment submitted.")
        st.session_state.comment_submitted = True

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# --- ADMIN SECTION ---
if "admin_access" not in st.session_state:
    st.session_state.admin_access = False

with st.expander("🔒 Admin Access"):
    pw = st.text_input("Enter admin password to view comments", type="password")
    if st.button("Login"):
        if pw == PASSWORD:
            st.session_state.admin_access = True
        else:
            st.error("Incorrect password.")

if st.session_state.admin_access:
    st.subheader("🗂️ All Comments")
    for c in load_json(COMMENTS_PATH):
        st.markdown(f"**{c['name']}** ({c['time']})")
        st.write(c["comment"])
        st.markdown("---")
