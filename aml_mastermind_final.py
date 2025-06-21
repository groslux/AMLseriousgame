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

# --- FILE I/O ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🏆 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🧠 Areas to Improve:")
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

# --- SESSION INIT ---
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
        "show_result": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# --- LOAD QUESTIONS ---
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

# --- MAIN APP ---
questions_data = load_questions()
grouped = group_by_category(questions_data)
leaderboard = load_json(LEADERBOARD_PATH)
player_count = len(leaderboard)

st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- NAME PAGE ---
if st.session_state.page == "name":
    st.title("AML Serious Game 🕵️")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players already participated: <b>{player_count}</b></div>", unsafe_allow_html=True)
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue"):
        if st.session_state.player_name.strip():
            st.session_state.page = "instructions"
        else:
            st.warning("Please enter a name.")

# --- INSTRUCTIONS PAGE ---
elif st.session_state.page == "instructions":
    st.title("🕹️ Instructions")
    st.markdown("""
### 🚨 Your Mission:
Test your AML skills across real-world scenarios!

- Choose Classic or Time Attack mode  
- Pick a topic: Crypto, Funds, or Banking  
- Submit answers and receive feedback immediately  
- Get a 🎓 certificate and 🏆 join the leaderboard!

### 📝 Disclaimer:
This game is for training purposes. There may be mistakes or simplifications. Nothing here is legal advice.

---

""")
    st.subheader("Choose Game Mode")
    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Category", list(grouped.keys()))
    if mode == "Classic Quiz":
        num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped.get(category, [])
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.game_ended = False
        st.session_state.leaderboard_saved = False
        st.session_state.submitted = False
        st.session_state.show_result = False

# --- QUIZ PAGE ---
elif st.session_state.page == "quiz":
    questions = st.session_state.questions
    q_idx = st.session_state.current
    if q_idx < len(questions):
        if st.session_state.mode == "Time Attack":
            remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
            if remaining <= 0:
                st.session_state.page = "results"
            else:
                st.markdown(f"⏱️ Time Left: **{remaining} seconds**")

        question = questions[q_idx]
        st.markdown(f"### Question {q_idx + 1}: {question['question']}")
        options_key = f"options_{q_idx}"
        if options_key not in st.session_state:
            opts = question["options"].copy()
            random.shuffle(opts)
            st.session_state[options_key] = opts
        selected = st.radio("Choose your answer:", st.session_state[options_key], key=f"radio_{q_idx}")

        if st.button("Submit Answer"):
            st.session_state["submitted"] = True
            correct = question["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            st.session_state.answers.append(picked == correct)
            st.session_state["last_explanation"] = question.get("explanation", "No explanation provided.")
            st.session_state["last_source"] = question.get("source", "Unknown")
            st.session_state["last_correct"] = question["correct_answer"]
            st.session_state.show_result = True

        if st.session_state.show_result:
            is_correct = st.session_state.answers[-1]
            st.success("✅ Correct!" if is_correct else f"❌ Wrong. Correct answer: {st.session_state['last_correct']}")
            st.info(st.session_state["last_explanation"])
            st.caption(f"📚 Source: {st.session_state['last_source']}")
            if st.button("Next"):
                st.session_state.current += 1
                st.session_state.submitted = False
                st.session_state.show_result = False
                if st.session_state.mode == "Time Attack" and time.time() - st.session_state.start_time >= st.session_state.time_limit:
                    st.session_state.page = "results"
    else:
        st.session_state.page = "results"

# --- RESULTS PAGE ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    st.title("✅ Game Complete!")
    st.markdown(f"**👤 Player:** {st.session_state.player_name}")
    st.markdown(f"**🎮 Mode:** {st.session_state.mode}")
    st.markdown(f"**📂 Category:** {st.session_state.category}")
    st.markdown(f"**📊 Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**⏱️ Time Taken:** {duration} seconds")

    if not st.session_state.leaderboard_saved and score > 0:
        leaderboard.append({
            "name": st.session_state.player_name.strip()[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        save_json(LEADERBOARD_PATH, leaderboard)
        st.session_state.leaderboard_saved = True

    incorrect_qs = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers)
        if not correct
    ]
    cert = generate_certificate(
        st.session_state.player_name, score, total, percent, duration, incorrect_qs
    )
    st.download_button("🎓 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("Show Leaderboard"):
        st.markdown("### 🏅 Top Players")
        top10 = sorted(leaderboard, key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top10, start=1):
            st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['mode']} | {r['duration']}s")

    st.markdown("---")
    st.subheader("📢 Leave a Comment")
    comment = st.text_area("Your comment (visible only to the game creator):")
    if st.button("Submit Comment"):
        if comment.strip():
            all_comments = load_json(COMMENTS_PATH)
            all_comments.append({
                "name": st.session_state.player_name[:5] + "###",
                "comment": comment.strip(),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            save_json(COMMENTS_PATH, all_comments)
            st.success("Comment submitted!")

    if st.button("🔁 Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

st.markdown("---")
st.caption("For AML/CFT Training - Luxembourg GROS - FATF & IMF inspired.")
