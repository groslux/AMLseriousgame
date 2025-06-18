
import streamlit as st
import json
import random
import time
from datetime import datetime
import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIGURATION ---
DATA_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = "leaderboard.json"
TIME_OPTIONS = [60, 120, 180]

# --- PAGE SETUP ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- LOADERS ---
@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_leaderboard(records):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "AML Mastermind Certificate")

    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 240, "Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, height - 240, "Areas to improve:")
        y = height - 260
        for q in incorrect_qs:
            c.setFont("Helvetica", 10)
            c.drawString(120, y, f"- {q['question'][:90]}...")
            y -= 14
            if y < 100:
                c.showPage()
                y = height - 100

    c.save()
    buffer.seek(0)
    return buffer

# --- SESSION STATE DEFAULTS ---
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
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- LOAD DATA ---
questions_data = load_questions()
grouped = group_by_category(questions_data)
leaderboard = load_leaderboard()
player_count = len([r for r in leaderboard if r.get("score", 0) > 0])

# --- UI: HEADER ---
st.title("AML Mastermind Deluxe")
st.markdown(f"<div style='text-align: center; font-size:18px;'>"
            f"Welcome to the ultimate anti-money laundering quiz.<br>"
            f"Players who have already played: <b>{player_count}</b>"
            f"</div>", unsafe_allow_html=True)
st.markdown("---")

# --- NAME INPUT ---
st.session_state.player_name = st.text_input("Enter your name to begin:")

if not st.session_state.player_name.strip():
    st.stop()

# --- GAME SETUP ---
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
        if not pool:
            st.error("No questions available in this category.")
            st.stop()

        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.submitted = False
        st.session_state.leaderboard_saved = False
        st.session_state.game_started = True
        st.session_state.game_ended = False
    else:
        st.stop()

# --- GAME LOOP ---
if not st.session_state.game_ended and st.session_state.current < len(st.session_state.questions):
    q_idx = st.session_state.current
    question = st.session_state.questions[q_idx]

    # Time check
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

        if is_correct:
            st.success("Correct!")
        else:
            st.error(f"Wrong. Correct answer: {question['correct_answer']}")

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
    st.markdown(f"Player: {st.session_state.player_name}")
    st.markdown(f"Mode: {st.session_state.mode}")
    st.markdown(f"Category: {st.session_state.category}")
    st.markdown(f"Score: {score}/{total} ({percent}%)")
    st.markdown(f"Time Taken: {duration} seconds")
    st.markdown(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if percent >= 75:
        st.success("Excellent! You've earned a certificate!")
    else:
        st.info("Keep practicing to improve your score!")

    if not st.session_state.leaderboard_saved and score > 0:
        leaderboard.append({
            "name": st.session_state.player_name.strip()[:3] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        save_leaderboard(leaderboard)
        st.session_state.leaderboard_saved = True

    incorrect_qs = [st.session_state.questions[i] for i, correct in enumerate(st.session_state.answers) if not correct]
    pdf_data = generate_certificate(
        st.session_state.player_name,
        score,
        total,
        percent,
        duration,
        incorrect_qs
    )

    st.download_button(
        label="Download your certificate",
        data=pdf_data,
        file_name=f"{st.session_state.player_name}_certificate.pdf",
        mime="application/pdf"
    )

    if st.checkbox("Show Leaderboard"):
        valid_entries = [r for r in leaderboard if r["score"] > 0]
        for r in valid_entries:
            r["efficiency"] = r["duration"] / r["score"]

        top10 = sorted(valid_entries, key=lambda x: x["efficiency"])[:10]

        st.markdown("### Top 10 Efficient Players")
        st.caption("Ranked by seconds per correct answer (lower is better)")

        for i, r in enumerate(top10, start=1):
            st.markdown(
                f"{i}. {r['name']} | {r['mode']} | {r['category']} | "
                f"{r['score']}/{r['total']} correct | "
                f"{r['duration']}s | {r['efficiency']:.2f} sec/correct"
            )

    if st.button("Play Again"):
        for k in list(defaults.keys()) + [f"options_{i}" for i in range(len(st.session_state.questions))]:
            st.session_state.pop(k, None)

st.markdown("---")
st.caption("Made for AML training – Powered by FATF, IOSCO, IMF & World Bank best practices.")
