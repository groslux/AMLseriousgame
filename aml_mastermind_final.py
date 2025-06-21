# 🔐 AML Mastermind Deluxe - Streamlit app
import streamlit as st
import json
import random
import time
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import pathlib

# --- CONFIGURATION ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]

# --- STATE INIT ---
def init_state():
    keys = {
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
        "game_started": False,
        "game_ended": False,
        "leaderboard_saved": False,
        "selected_answer": None,
        "show_feedback": False,
        "admin_logged_in": False
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# --- DATA UTILS ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(questions):
    grouped = {}
    for q in questions:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

def append_to_file(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

# --- LEADERBOARD ---
def get_top_players():
    return sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]

# --- CERTIFICATE ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏅 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"👤 Name: {name}")
    c.drawString(100, height - 160, f"🧠 Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"⏱ Duration: {duration} sec")
    c.drawString(100, height - 200, f"📆 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.drawString(100, y, "🎉 Excellent performance! 🕵️‍♂️")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
                f"ℹ {q.get('explanation', 'No explanation.')}"
            ]
            for line in lines:
                wrapped = [line[i:i+90] for i in range(0, len(line), 90)]
                for subline in wrapped:
                    c.setFont("Helvetica", 10)
                    c.drawString(110, y, subline)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 8
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGE NAVIGATION ---
st.set_page_config("AML Mastermind Deluxe", layout="centered")
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

if st.session_state["page"] == "name":
    st.title("AML Mastermind Deluxe 🕵️‍♂️")
    st.markdown(f"🎮 **Players who played:** {player_count}")
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.session_state.player_name.strip():
        if st.button("Continue"):
            st.session_state.page = "intro"

elif st.session_state["page"] == "intro":
    st.markdown("## Welcome to the AML Serious Game for Supervisors 🛡️")
    st.markdown("""
**🚨 Your Mission:**  
Test your AML/CFT reflexes through real-world questions.

### How the Game Works:
- Choose *Classic* or *Time Attack*
- Pick a topic: Crypto, Banking, Funds
- Answer carefully. One click on Submit shows the answer and explanation.
- Then click **Next** to go forward.

**📜 Results:**
- You get a certificate
- Join the leaderboard
- Leave anonymous feedback

📝 *Disclaimer:* This game is for educational use. There may be simplifications or errors. No legal advice.
""")
    if st.button("Start Game Setup"):
        st.session_state.page = "setup"

elif st.session_state["page"] == "setup":
    st.subheader("Choose your game mode & category")
    st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Topic", list(grouped.keys()))
    if st.session_state.mode == "Classic Quiz":
        qn = st.slider("How many questions?", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (sec)", TIME_OPTIONS)

    if st.button("Begin Game"):
        pool = grouped.get(st.session_state.category, [])[:]
        random.shuffle(pool)
        st.session_state.questions = pool[:qn] if st.session_state.mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if st.session_state.mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.show_feedback = False

elif st.session_state["page"] == "quiz":
    q_idx = st.session_state.current
    total = len(st.session_state.questions)

    if q_idx >= total or (
        st.session_state.mode == "Time Attack"
        and (time.time() - st.session_state.start_time) > st.session_state.time_limit
    ):
        st.session_state.page = "results"
        st.rerun()

    question = st.session_state.questions[q_idx]
    st.markdown(f"**Question {q_idx + 1}/{total}**")
    st.markdown(f"🧩 *{question['question']}*")

    if f"options_{q_idx}" not in st.session_state:
        opts = question["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{q_idx}"] = opts

    selected = st.radio("Your answer:", st.session_state[f"options_{q_idx}"], key=f"radio_{q_idx}")

    if not st.session_state.show_feedback:
        if st.button("Submit"):
            st.session_state.selected_answer = selected
            correct = question["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.session_state.show_feedback = True
            st.success("✅ Correct!" if is_correct else f"❌ Incorrect! Correct: {question['correct_answer']}")
            st.info(question.get("explanation", "No explanation provided."))
            st.caption(f"📚 Source: {question.get('source', 'Unknown')}")

    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.show_feedback = False
            st.rerun()

elif st.session_state["page"] == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.success("✅ Game Complete!")
    st.markdown(f"**{st.session_state.player_name}**")
    st.markdown(f"**Mode:** {st.session_state.mode} | **Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} sec | **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not st.session_state.leaderboard_saved:
        record = {
            "name": st.session_state.player_name[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        append_to_file(LEADERBOARD_PATH, record)
        st.session_state.leaderboard_saved = True

    cert = generate_certificate(
        st.session_state.player_name, score, total, percent, duration,
        [st.session_state.questions[i] for i, correct in enumerate(st.session_state.answers) if not correct]
    )
    st.download_button("📄 Download Certificate", cert, "AML_Certificate.pdf", "application/pdf")

    st.markdown("### 🏆 Leaderboard")
    for i, r in enumerate(get_top_players(), 1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s")

    st.markdown("### 💬 Leave a private comment")
    comment = st.text_area("Your comment (visible only to game creator):")
    if st.button("Submit Comment") and comment.strip():
        append_to_file(COMMENTS_PATH, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Comment submitted!")

    st.markdown("---")
    st.caption("All comments are private and not visible to other players.")

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# --- ADMIN PANEL ---
if st.sidebar.text_input("Admin Password", type="password") == "iloveaml2025":
    st.sidebar.markdown("### 🗂️ Comments")
    for c in load_json(COMMENTS_PATH):
        st.sidebar.markdown(f"**{c['name']}** ({c.get('time', '-')})")
        st.sidebar.write(c["comment"])
