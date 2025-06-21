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

# --- SETUP ---
st.set_page_config(page_title="AML Serious Game for Supervisors", layout="centered")

# --- FUNCTIONS ---
def load_json_file(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_file(path, record):
    data = load_json_file(path)
    data.append(record)
    save_json_file(path, data)

def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

def get_top_players():
    data = load_json_file(LEADERBOARD_PATH)
    return sorted(data, key=lambda x: (-x["score"], x["duration"]))[:10]

def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏆 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🛠 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica-Bold", 10)
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation')}"
            ]
            for line in lines:
                for sub in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(110, y, sub)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- STATE ---
if "page" not in st.session_state:
    st.session_state.page = "name"
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "mode" not in st.session_state:
    st.session_state.mode = None
if "category" not in st.session_state:
    st.session_state.category = None
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current" not in st.session_state:
    st.session_state.current = 0
if "answers" not in st.session_state:
    st.session_state.answers = []
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "time_limit" not in st.session_state:
    st.session_state.time_limit = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "game_over" not in st.session_state:
    st.session_state.game_over = False

questions_data = load_questions()
grouped = group_by_category(questions_data)

# --- PAGE 1: NAME ---
if st.session_state.page == "name":
    st.title("AML Serious Game")
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue"):
        if st.session_state.player_name.strip():
            st.session_state.page = "intro"

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.page == "intro":
    st.title("🕵️ AML Serious Game for Supervisors")
    st.markdown(f"👥 Players so far: **{len(load_json_file(LEADERBOARD_PATH))}**")
    st.markdown("""
    **🚨 Your Mission:**  
    Read the questions, analyze the answers and make the right call.

    🔍 Test your AML skills  
    💰 Learn AML/CFT facts from Banking, Crypto, and Investment Funds  
    📜 Earn your certificate  
    🏆 Join the leaderboard!

    ### Disclaimer:
    This game is for training only. There may be mistakes or simplifications. No legal advice.

    ### How it works:
    - Choose your mode (Classic or Time Attack)
    - Choose a topic
    - Answer the questions
    - Get a certificate and leaderboard ranking
    """)

    mode = st.selectbox("Choose mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Choose category", list(grouped.keys()))

    if mode == "Classic Quiz":
        num_q = st.slider("Number of questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped[category]
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_q] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.page = "quiz"

# --- PAGE 3: QUIZ ---
elif st.session_state.page == "quiz":
    questions = st.session_state.questions
    idx = st.session_state.current
    total = len(questions)

    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
        else:
            st.markdown(f"⏱ Time Left: **{remaining} seconds**")

    if idx < total:
        q = questions[idx]
        st.markdown(f"### Question {idx+1}: {q['question']}")
        options = q['options'].copy()
        random.shuffle(options)
        selected = st.radio("Your answer:", options, key=f"q_{idx}")

        if not st.session_state.submitted:
            if st.button("Submit"):
                st.session_state.submitted = True
                st.session_state.correct_answer = q["correct_answer"]
                st.session_state.user_answer = selected
                is_correct = selected.lower() == q["correct_answer"].lower()
                st.session_state.answers.append(is_correct)
                st.success("✅ Correct!" if is_correct else f"❌ Incorrect. Correct: {q['correct_answer']}")
                st.info(q.get("explanation", "No explanation provided."))
                st.caption(f"📚 Source: {q.get('source', 'Unknown')}")

        elif st.button("Next Question"):
            st.session_state.submitted = False
            st.session_state.current += 1
            if st.session_state.current >= total or (
                st.session_state.mode == "Time Attack"
                and time.time() - st.session_state.start_time >= st.session_state.time_limit
            ):
                st.session_state.page = "results"
    else:
        st.session_state.page = "results"

# --- PAGE 4: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.questions)
    correct = sum(st.session_state.answers)
    percent = round(correct / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.title("📊 Results")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {correct}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")

    append_to_file(LEADERBOARD_PATH, {
        "name": st.session_state.player_name.strip()[:5] + "###",
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "score": correct,
        "total": total,
        "percent": percent,
        "duration": duration,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    incorrect_qs = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers)
        if not correct
    ]
    cert = generate_certificate(st.session_state.player_name, correct, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("### 🧠 Leave a comment (visible only to the creator):")
    comment = st.text_area("Your feedback:", key="comment_area")
    if st.button("Submit Comment"):
        append_to_file(COMMENTS_PATH, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you for your feedback! It won't be visible to other players.")

    st.markdown("### 🏆 Leaderboard (Top 10)")
    for i, r in enumerate(get_top_players(), 1):
        st.markdown(
            f"{i}. {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} | {r['duration']}s"
        )

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()
