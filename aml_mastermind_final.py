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

# --- UTILS ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

def get_top_players():
    data = load_json(LEADERBOARD_PATH)
    return sorted(data, key=lambda x: (-x['score'], x['duration']))[:10]

def get_player_count():
    return len(load_json(LEADERBOARD_PATH))

# --- CERTIFICATE ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🎓 AML Serious Game Certificate")
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
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica-Bold", 10)
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]
            for line in lines:
                for subline in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(110, y, subline)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
        topics = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for cat in topics:
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

# --- INIT STATE ---
if "page" not in st.session_state:
    st.session_state.page = "intro"
if "answers" not in st.session_state:
    st.session_state.answers = []

questions_data = load_questions()
grouped = group_by_category(questions_data)

# --- INTRO PAGE ---
if st.session_state.page == "intro":
    st.title("🕵️ AML Serious Game for Supervisors")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{get_player_count()}</b></div>", unsafe_allow_html=True)

    st.markdown("""
    **🚨 Your Mission:**  
    Read the questions, analyze the answers and make the right call.

    🔍 Test your AML skills  
    💰 Learn AML/CFT facts from Banking, Crypto, and Investment Funds  
    📜 Earn your certificate  
    🏆 Join the leaderboard!

    ### 📝 Disclaimer:
    This game is for educational purposes only. There may be simplifications or mistakes. It is not professional advice.

    ---""")

    st.session_state.player_name = st.text_input("Enter your name:")
    mode = st.selectbox("Choose Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Select Category", list(grouped.keys()))
    if mode == "Classic Quiz":
        num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped[category]
        random.shuffle(pool)
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.page = "quiz"
        st.rerun()

# --- QUIZ PAGE ---
if st.session_state.page == "quiz":
    idx = st.session_state.current
    question = st.session_state.questions[idx]

    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
            st.rerun()
        st.markdown(f"⏱️ Time Left: **{remaining} sec**")

    st.markdown(f"### Question {idx+1}: {question['question']}")
    options = st.radio("Options:", question["options"], key=f"q_{idx}")
    if st.button("Submit", key=f"s_{idx}"):
        correct = question["correct_answer"].strip().lower()
        picked = options.strip().lower()
        st.session_state.answers.append(picked == correct)
        st.session_state.current += 1
        if st.session_state.current >= len(st.session_state.questions):
            st.session_state.page = "results"
        st.rerun()

# --- RESULTS PAGE ---
if st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    name = st.session_state.player_name.strip()[:5] + "###"

    st.title("🎯 Game Complete!")
    st.markdown(f"**👤 Player:** {st.session_state.player_name}")
    st.markdown(f"**📊 Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**🕒 Duration:** {duration} sec")
    st.markdown(f"**📅 Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not any(d['name'] == name and d['timestamp'].startswith(datetime.now().strftime('%Y-%m-%d')) for d in load_json(LEADERBOARD_PATH)):
        append_json(LEADERBOARD_PATH, {
            "name": name,
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    incorrect_qs = [st.session_state.questions[i] for i, c in enumerate(st.session_state.answers) if not c]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", data=cert, file_name="certificate.pdf", mime="application/pdf")

    with st.expander("🏆 Leaderboard"):
        top10 = get_top_players()
        for i, r in enumerate(top10, start=1):
            st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['category']}")

    st.markdown("---")
    st.markdown("### 💬 Leave a comment (visible only to the game creator)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment"):
        if comment.strip():
            append_json(COMMENTS_PATH, {
                "name": st.session_state.player_name.strip(),
                "comment": comment.strip(),
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            st.success("Comment submitted!")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "intro"
        st.rerun()
