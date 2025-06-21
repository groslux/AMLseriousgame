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

# --- UTILS: LEADERBOARD ---
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
    leaderboard = load_leaderboard()
    leaderboard.append(record)
    save_leaderboard(leaderboard)

def get_player_count():
    return len(load_leaderboard())

def get_top_players():
    return sorted(load_leaderboard(), key=lambda x: (-x['score'], x['duration']))[:10]

# --- UTILS: COMMENTS ---
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
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "⚠️ Areas to Improve (based on incorrect answers):")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica-Bold", 10)
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]
            for line in lines:
                wrapped = [line[i:i+100] for i in range(0, len(line), 100)]
                for subline in wrapped:
                    c.drawString(110, y, subline)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
        categories = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "📚 Suggested Topics to Review:")
        y -= 16
        for cat in categories:
            c.setFont("Helvetica", 10)
            c.drawString(120, y, f"- {cat}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 80
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGE SETUP ---
st.set_page_config(page_title="AML Serious Game", layout="centered")
questions_data = json.load(open("questions_cleaned.json", encoding="utf-8"))

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

# --- STATE INIT ---
def init_state():
    defaults = {
        "page": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "answers": [],
        "current": 0,
        "submitted": False,
        "show_next": False,
        "start_time": None,
        "time_limit": None,
        "score": 0,
        "game_ended": False,
        "leaderboard_saved": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- PAGE: NAME ---
if st.session_state.page == "name":
    st.title("🕵️ AML Serious Game for Supervisors")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)
    name = st.text_input("Enter your name to begin:")
    if name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"


# --- PAGE: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.markdown("## 🔍 Welcome to the AML Serious Game")
    st.markdown("""
**🚨 Your Mission:**  
Answer the questions based on your AML knowledge!

🔎 Topics: Banking, Crypto, Investment Funds  
🧠 Modes: Classic or Time Attack  
📜 Earn a certificate  
🏆 Join the leaderboard

**Disclaimer**: This game is for educational purposes only. There may be simplifications or inaccuracies. It does not constitute advice.
    """)
    mode = st.selectbox("Select your game mode:", ["Classic", "Time Attack"])
    category = st.selectbox("Choose a topic:", list(grouped.keys()))
    if mode == "Classic":
        num_questions = st.slider("Number of questions:", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time limit in seconds:", TIME_OPTIONS)

    if st.button("Start Game"):
        st.session_state.mode = mode
        st.session_state.category = category
        questions = grouped[category]
        random.shuffle(questions)
        st.session_state.questions = questions[:num_questions] if mode == "Classic" else questions
        st.session_state.start_time = time.time()
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.page = "quiz"
   

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        st.markdown(f"⏱️ Time Left: {remaining} seconds")
        if remaining <= 0:
            st.session_state.page = "results"
      

    idx = st.session_state["current"]
    if idx >= len(st.session_state.questions):
        st.session_state.page = "results"


    q = st.session_state.questions[idx]
    if f"options_{idx}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{idx}"] = opts

    st.markdown(f"### Question {idx + 1}/{len(st.session_state.questions)}")
    st.markdown(q["question"])
    selected = st.radio("Choose your answer:", st.session_state[f"options_{idx}"], key=f"q_{idx}")

    if not st.session_state.submitted:
        if st.button("Submit"):
            st.session_state.submitted = True
            st.session_state.selected_answer = selected
    else:
        correct = q["correct_answer"]
        is_correct = selected.strip().lower() == correct.strip().lower()
        st.success("✅ Correct!" if is_correct else f"❌ Wrong. Correct answer: {correct}")
        st.info(q.get("explanation", "No explanation provided."))
        st.caption(f"📚 Source: {q.get('source', 'N/A')}")
        st.session_state.answers.append(is_correct)
        st.session_state.submitted = False
        st.session_state.current += 1
        if st.button("Next Question"):
        

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.questions)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.markdown("## 🎯 Results")
    st.write(f"**Player**: {st.session_state.player_name}")
    st.write(f"**Score**: {score}/{total} ({percent}%)")
    st.write(f"**Duration**: {duration} seconds")

    if not st.session_state.leaderboard_saved:
        append_to_leaderboard({
            "name": st.session_state.player_name[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.session_state.leaderboard_saved = True

    incorrect_qs = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", cert, "AML_Certificate.pdf")

    st.markdown("### 🏆 Leaderboard")
    top = get_top_players()
    for i, p in enumerate(top, 1):
        st.markdown(f"{i}. {p['name']} | {p['score']}/{p['total']} | {p['duration']}s | {p['category']}")

    st.markdown("### 💬 Leave a comment for the game creator")
    comment_text = st.text_area("Your comment (visible only to the game creator):")
    if st.button("Submit Comment"):
        append_comment({
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment_text,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thank you for your feedback!")

    st.markdown("### 🔐 Admin Section")
    admin_pw = st.text_input("Enter admin password to view comments:", type="password")
    if admin_pw == "iloveaml2025":
        st.markdown("### 📥 Player Comments")
        comments = load_comments()
        for c in comments:
            st.markdown(f"**{c['name']}** ({c['time']})")
            st.write(c['comment'])

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
 
