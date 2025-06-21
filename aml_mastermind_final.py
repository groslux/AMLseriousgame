import streamlit as st
import json
import random
import time
import os
import pathlib
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]

# --- LOCAL STORAGE ---
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

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "📜 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Excellent job!")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🧠 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
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
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for cat in sorted(set(q.get("category", "Other") for q in incorrect_qs)):
            c.drawString(120, y, f"- {cat}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 80
    c.save()
    buffer.seek(0)
    return buffer

# --- DATA ---
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

# --- STATE INIT ---
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
        "show_result": False,
        "show_leaderboard": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- NAME PAGE ---
if st.session_state.page == "name":
    st.title("🔐 Enter the AML Arena")
    st.markdown(f"**🧑‍💼 Players who have already played: {player_count}**")
    name = st.text_input("Enter your name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"
        st.rerun()

# --- INSTRUCTIONS PAGE ---
elif st.session_state.page == "instructions":
    st.title("🕵️ AML Serious Game Instructions")
    st.markdown("""
    **🚨 Your Mission:**  
    Read the questions, analyze the answers and make the right call.

    🔍 Test your AML skills  
    💰 Learn AML/CFT facts from Banking, Crypto, and Investment Funds  
    📜 Earn your certificate  
    🏆 Join the leaderboard!

    ---
    ### 📝 Disclaimer:
    This game is for training purposes only. There may be simplifications or approximations. This is not legal advice.

    ---
    """)
    mode = st.selectbox("Choose Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Choose Category", list(grouped.keys()))
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
        st.session_state.page = "quiz"
        st.rerun()

# --- QUIZ PAGE ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.game_ended = True
            st.session_state.page = "results"
            st.rerun()
        else:
            st.markdown(f"⏳ Time Left: **{remaining} seconds**")

    q_idx = st.session_state.current
    if q_idx < len(st.session_state.questions):
        question = st.session_state.questions[q_idx]
        if f"options_{q_idx}" not in st.session_state:
            opts = question["options"].copy()
            random.shuffle(opts)
            st.session_state[f"options_{q_idx}"] = opts
        st.markdown(f"### ❓ Question {q_idx+1}: {question['question']}")
        selected = st.radio("Choose your answer:", st.session_state[f"options_{q_idx}"], key=f"answer_{q_idx}")
        if st.button("Submit Answer", key=f"submit_{q_idx}") and not st.session_state.submitted:
            st.session_state.submitted = True
            correct = question["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.success("✅ Correct!" if is_correct else f"❌ Incorrect. Correct answer: {question['correct_answer']}")
            st.info(question.get("explanation", "No explanation."))
            st.caption(f"📚 Source: {question.get('source', 'Unknown')}")
        if st.session_state.submitted and st.button("Next"):
            st.session_state.submitted = False
            st.session_state.current += 1
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"
            st.rerun()
    else:
        st.session_state.page = "results"
        st.rerun()

# --- RESULTS PAGE ---
elif st.session_state.page == "results":
    st.title("🎯 Quiz Results")
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.markdown(f"**👤 Player:** {st.session_state.player_name}")
    st.markdown(f"**📚 Category:** {st.session_state.category}")
    st.markdown(f"**🎮 Mode:** {st.session_state.mode}")
    st.markdown(f"**✅ Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**⏱️ Duration:** {duration} seconds")

    if not st.session_state.leaderboard_saved:
        append_json(LEADERBOARD_PATH, {
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

    incorrect_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("🏆 Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(
                f"{i}. {r.get('name', '???')} | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}"
            )

    st.markdown("---")
    st.subheader("💬 Leave a comment for the game creator")
    st.caption("Comments are private and only visible to the game creator.")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_PATH, {
            "player": st.session_state.player_name,
            "comment": comment.strip(),
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.success("Thank you for your feedback!")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- FOOTER ---
st.markdown("---")
st.caption("🛡️ Designed for AML training of Supervisors — Based on FATF, IOSCO, IMF & World Bank reports.")
