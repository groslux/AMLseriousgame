import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIG ---
SHEET_NAME = "AML_Leaderboard"
TIME_OPTIONS = [60, 120, 180]

# --- GOOGLE SHEET CONNECTION ---
def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    return sheet

def save_to_sheet(record):
    sheet = connect_to_sheet()
    sheet.append_row([record[k] for k in ["name", "mode", "category", "score", "total", "percent", "duration", "timestamp"]])

def get_leaderboard():
    sheet = connect_to_sheet()
    return sheet.get_all_records()

def get_player_count():
    return len(get_leaderboard())

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
        c.drawString(100, y, "Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "Areas to Improve (based on incorrect answers):")
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

# --- PAGE INIT ---
st.set_page_config(page_title="AML Serious Game for Supervisors", layout="centered")

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

# --- STATE ---
def init_state():
    defaults = {
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "game_started": False,
        "game_ended": False,
        "submitted": False,
        "leaderboard_saved": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- UI ---
st.title("AML Serious Game for Supervisors")
st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)
st.markdown("---")

st.session_state.player_name = st.text_input("Enter your name to begin:")
if not st.session_state.player_name.strip():
    st.info("Please enter your name above to continue.")
    st.stop()

st.markdown("""
## Welcome to the 1st AML Serious Game for Supervisors

**Disclaimer**: This game is for educational and training purposes only. No legal advice.

### How the Game Works:
- Choose Classic or Time Attack mode
- Select a topic: Crypto, Investment Funds, or Banking
- In each question, click Submit twice to proceed.

### Results:
- You get a certificate, leaderboard rank, and feedback.
""")

if not st.session_state.game_started:
    st.subheader("Choose your game mode")
    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Select a Category", list(grouped.keys()))

    if mode == "Classic Quiz":
        num_questions = st.slider("How many questions?", 5, 30, 10)
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
        st.session_state.game_started = True
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.submitted = False
        st.session_state.leaderboard_saved = False
        st.session_state.game_ended = False
    else:
        st.stop()

# --- GAME LOOP ---
if not st.session_state.game_ended and st.session_state.current < len(st.session_state.questions):
    q_idx = st.session_state.current
    question = st.session_state.questions[q_idx]

    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.game_ended = True
        else:
            st.markdown(f"Time Left: **{remaining} seconds**")

    if f"options_{q_idx}" not in st.session_state:
        options = question["options"].copy()
        random.shuffle(options)
        st.session_state[f"options_{q_idx}"] = options

    options = st.session_state[f"options_{q_idx}"]
    st.markdown(f"### Question {q_idx + 1}: {question['question']}")
    selected = st.radio("Choose your answer:", options, key=f"answer_{q_idx}")

    if st.button("Submit Answer", key=f"submit_{q_idx}"):
        st.session_state.submitted = True
        st.session_state.selected_answer = selected

    if st.session_state.submitted:
        st.session_state.submitted = False
        correct = question["correct_answer"].strip().lower()
        picked = st.session_state.selected_answer.strip().lower()
        is_correct = picked == correct
        st.session_state.answers.append(is_correct)
        st.success("Correct!" if is_correct else f"Wrong. Correct answer: {question['correct_answer']}")
        st.info(question.get("explanation", "No explanation provided."))
        st.caption(f"Source: {question.get('source', 'Unknown')}")
        st.session_state.current += 1

# --- RESULTS ---
if st.session_state.game_ended or st.session_state.current >= len(st.session_state.questions):
    st.session_state.game_ended = True
    score = sum(st.session_state.answers)
    total = st.session_state.current
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## Game Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not st.session_state.leaderboard_saved and score > 0:
        save_to_sheet({
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

    incorrect_qs = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers)
        if not correct
    ]
    cert_buffer = generate_certificate(
        st.session_state.player_name, score, total, percent, duration, incorrect_qs
    )
    st.download_button("📄 Download Your Certificate", data=cert_buffer, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("Show Leaderboard"):
        top10 = sorted(
            get_leaderboard(),
            key=lambda x: (-x.get("score", 0), x.get("duration", 99999))
        )[:10]
        st.markdown("### Top 10 Players")
        st.caption("Ranked by highest score, then fastest time")
        for i, r in enumerate(top10, start=1):
            st.markdown(
                f"{i}. {r.get('name', '???')} | {r.get('mode', '-') } | {r.get('category', '-') } | "
                f"{r.get('score', 0)}/{r.get('total', 0)} correct | "
                f"{r.get('duration', 0)}s"
            )

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]

st.markdown("---")
st.caption("Designed for AML training of Supervisors - GROS - Luxembourg – based on FATF, IOSCO, IMF & World Bank public reports.")
