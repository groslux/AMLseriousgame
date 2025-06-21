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

# --- GAME UTILS ---
def load_leaderboard():
    return load_json(LEADERBOARD_PATH)

def append_to_leaderboard(record):
    data = load_leaderboard()
    data.append(record)
    save_json(LEADERBOARD_PATH, data)

def get_player_count():
    return len(load_leaderboard())

def get_top_players():
    return sorted(load_leaderboard(), key=lambda x: (-x['score'], x['duration']))[:10]

def load_comments():
    return load_json(COMMENTS_PATH)

def append_comment(comment):
    data = load_comments()
    data.append(comment)
    save_json(COMMENTS_PATH, data)

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
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "❗ Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation.')}"
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
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for cat in categories:
            c.setFont("Helvetica", 10)
            c.drawString(120, y, f"- {cat}")
            y -= 12
    c.save()
    buffer.seek(0)
    return buffer

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

# --- INIT STATE ---
def init_state():
    defaults = {
        "step": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "submitted": False,
        "leaderboard_saved": False,
        "show_feedback": False,
        "selected_answer": None
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- PAGE LOGIC ---
st.set_page_config("AML Serious Game", layout="centered")

if st.session_state.step == "name":
    st.title("AML Serious Game for Supervisors")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue") and st.session_state.player_name.strip():
        st.session_state.step = "instructions"
        st.rerun()

elif st.session_state.step == "instructions":
    st.markdown("## 🕵️ Welcome to the AML Serious Game for Supervisors")
    st.markdown("""
    **🚨 Your Mission:**  
    Read the questions, analyze the answers and make the right call.

    🔍 Test your AML skills  
    💰 Learn AML/CFT facts from Banking, Crypto, and Investment Funds  
    📜 Earn your certificate  
    🏆 Join the leaderboard!

    ### 📝 Disclaimer:
    This game is for training only. There may be simplifications or errors. It is not professional advice.

    ### How to Play:
    - Choose Classic or Time Attack
    - Pick a topic
    - Click once to submit an answer and see feedback before continuing.
    """)
    if st.button("Start the Game"):
        st.session_state.step = "quiz"
        st.rerun()

elif st.session_state.step == "quiz":
    if not st.session_state.questions:
        st.subheader("Choose your game mode")
        st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
        st.session_state.category = st.selectbox("Topic", list(grouped.keys()))
        if st.session_state.mode == "Classic Quiz":
            num_questions = st.slider("How many questions?", 5, 30, 10)
        else:
            st.session_state.time_limit = st.selectbox("Time Limit", TIME_OPTIONS)
        if st.button("Start Quiz"):
            pool = grouped.get(st.session_state.category, [])
            random.shuffle(pool)
            st.session_state.questions = pool[:num_questions] if st.session_state.mode == "Classic Quiz" else pool
            st.session_state.start_time = time.time()
            st.session_state.current = 0
            st.rerun()
        st.stop()

    if st.session_state.current >= len(st.session_state.questions) or (
        st.session_state.mode == "Time Attack" and time.time() - st.session_state.start_time > st.session_state.time_limit
    ):
        st.session_state.step = "results"
        st.rerun()

    question = st.session_state.questions[st.session_state.current]
    if f"options_{st.session_state.current}" not in st.session_state:
        st.session_state[f"options_{st.session_state.current}"] = random.sample(question["options"], len(question["options"]))
    options = st.session_state[f"options_{st.session_state.current}"]
    st.markdown(f"### Q{st.session_state.current + 1}: {question['question']}")
    selected = st.radio("Choose:", options, key=f"answer_{st.session_state.current}")

    if st.button("Submit Answer"):
        st.session_state.selected_answer = selected
        is_correct = selected.strip().lower() == question["correct_answer"].strip().lower()
        st.session_state.answers.append(is_correct)
        st.session_state.show_feedback = True

    if st.session_state.show_feedback:
        if st.session_state.answers[-1]:
            st.success("Correct ✅")
        else:
            st.error(f"Incorrect ❌ – Correct: {question['correct_answer']}")
        st.info(question.get("explanation", "No explanation provided."))
        st.caption(f"Source: {question.get('source', 'Unknown')}")
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.show_feedback = False
            st.rerun()

elif st.session_state.step == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.header("✅ Game Over")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} seconds")

    if not st.session_state.leaderboard_saved:
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
        st.session_state.leaderboard_saved = True

    incorrect_qs = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("Show Leaderboard"):
        st.markdown("### 🏆 Top 10 Players")
        for i, r in enumerate(get_top_players(), 1):
            st.markdown(
                f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}"
            )

    st.markdown("---")
    st.markdown("### 💬 Leave a comment for the creator")
    comment = st.text_area("Your comment (private):")
    if st.button("Submit Comment") and comment.strip():
        append_comment({
            "name": st.session_state.player_name[:5] + "###",
            "timestamp": datetime.now().isoformat(),
            "comment": comment.strip()
        })
        st.success("Comment saved. Only the creator can see it.")
    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
