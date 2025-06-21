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

# --- UTILITIES ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json(record, path):
    data = load_json(path)
    data.append(record)
    save_json(data, path)

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🕵️ AML Serious Game Certificate")
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
        c.drawString(100, y, "⚠️ Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
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
        "leaderboard_saved": False,
        "show_feedback": False,
        "last_feedback": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- START ---
init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

# --- INTRO PAGE ---
if not st.session_state.game_started and not st.session_state.game_ended:
    st.title("🕵️ AML Serious Game for Supervisors")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)

    st.markdown("## 👋 Welcome to the AML Serious Game!")
    st.markdown("""
**🚨 Your Mission:**  
Answer AML-themed questions based on Crypto, Investment Funds, or Banking.

🎯 Modes: Classic or Time Attack  
📜 Earn your Certificate  
🏆 Join the Leaderboard

🛡️ **Disclaimer:**  
This game is for educational and training purposes only.  
There may be approximations or simplifications.  
It does not constitute professional advice.

---

### Get Started:
""")

    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if not st.session_state.player_name.strip():
        st.stop()

    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Topic", list(grouped.keys()))
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

# --- GAME LOOP ---
if st.session_state.game_started and not st.session_state.game_ended:
    q_idx = st.session_state.current
    if q_idx >= len(st.session_state.questions):
        st.session_state.game_ended = True
        st.rerun()

    question = st.session_state.questions[q_idx]
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.game_ended = True
            st.rerun()
        else:
            st.markdown(f"⏱️ Time Left: **{remaining} seconds**")

    options = st.session_state.get(f"options_{q_idx}", random.sample(question["options"], len(question["options"])))
    st.session_state[f"options_{q_idx}"] = options
    st.markdown(f"### ❓ Question {q_idx + 1}: {question['question']}")
    selected = st.radio("Choose your answer:", options, key=f"answer_{q_idx}")

    if st.button("Submit Answer", key=f"submit_{q_idx}"):
        correct = question["correct_answer"].strip().lower()
        picked = selected.strip().lower()
        is_correct = picked == correct
        st.session_state.answers.append(is_correct)
        st.session_state.last_feedback = {
            "correct": is_correct,
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation", "No explanation provided."),
            "source": question.get("source", "Unknown")
        }
        st.session_state.current += 1
        st.session_state.show_feedback = True
        st.rerun()

# --- FEEDBACK ---
if st.session_state.show_feedback and st.session_state.last_feedback:
    fb = st.session_state.last_feedback
    st.success("✅ Correct!" if fb["correct"] else f"❌ Wrong. Correct answer: {fb['correct_answer']}")
    st.info(f"ℹ️ {fb['explanation']}")
    st.caption(f"📚 Source: {fb['source']}")
    st.session_state.show_feedback = False

# --- RESULTS ---
if st.session_state.game_ended:
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown("## ✅ Game Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")
    st.markdown(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not st.session_state.leaderboard_saved and score > 0:
        append_to_json({
            "name": st.session_state.player_name.strip()[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, LEADERBOARD_PATH)
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

    if st.checkbox("🏆 Show Leaderboard"):
        top10 = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top10, 1):
            st.markdown(
                f"{i}. {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} | {r['duration']}s"
            )

    st.markdown("### 💬 Leave a Comment (visible only to the game creator):")
    comment = st.text_area("Your feedback (optional):")
    if st.button("Send Comment"):
        if comment.strip():
            append_to_json({
                "name": st.session_state.player_name,
                "comment": comment,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, COMMENTS_PATH)
            st.success("✅ Thank you! Your comment has been received.")

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.markdown("---")
st.caption("Built for AML supervisory training – GROS – Luxembourg – content based on FATF, IMF & IOSCO public reports.")
