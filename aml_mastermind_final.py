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
ADMIN_PASSWORD = "iloveaml2025"

# --- JSON STORAGE ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

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
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
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
        topics = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for topic in topics:
            c.drawString(120, y, f"- {topic}")
            y -= 12
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGE INIT ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

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
    st.session_state.setdefault("page", "name")
    st.session_state.setdefault("player_name", "")
    st.session_state.setdefault("mode", None)
    st.session_state.setdefault("category", None)
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("current", 0)
    st.session_state.setdefault("answers", [])
    st.session_state.setdefault("start_time", None)
    st.session_state.setdefault("time_limit", None)
    st.session_state.setdefault("submitted", False)
    st.session_state.setdefault("selected_answer", None)
    st.session_state.setdefault("show_admin", False)

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

# --- PAGE: NAME ---
if st.session_state.page == "name":
    st.title("AML Serious Game")
    st.markdown(f"👥 **Players so far:** {player_count}")
    name = st.text_input("Enter your name to begin:")
    if name:
        st.session_state.player_name = name
        st.session_state.page = "instructions"

# --- PAGE: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.title("🎯 Welcome to the AML Serious Game")
    st.markdown("""
    🕵️ **Your Mission:** Detect red flags and apply AML knowledge  
    💼 **Topics:** Crypto, Investment Funds, Banking  
    🧠 **Modes:**  
    - Classic = fixed number of questions  
    - Time Attack = race against the clock

    📜 At the end, you’ll get a certificate, feedback, and see the leaderboard.

    ⚠️ **Disclaimer**: This game is for educational purposes only. It may contain simplifications and is not professional advice.
    """)
    st.session_state.mode = st.selectbox("Select game mode", ["Classic", "Time Attack"])
    st.session_state.category = st.selectbox("Select topic", list(grouped.keys()))
    if st.session_state.mode == "Classic":
        num_questions = st.slider("Number of questions", 5, 20, 10)
    else:
        st.session_state.time_limit = st.selectbox("Time limit (seconds)", TIME_OPTIONS)

    if st.button("Start Game"):
        q_pool = grouped.get(st.session_state.category, []).copy()
        random.shuffle(q_pool)
        st.session_state.questions = q_pool[:num_questions] if st.session_state.mode == "Classic" else q_pool
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.submitted = False
        st.session_state.selected_answer = None

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    i = st.session_state.current
    questions = st.session_state.questions
    q = questions[i]
    st.markdown(f"### Question {i+1}/{len(questions)}")
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        st.markdown(f"⏱️ Time left: **{remaining} seconds**")
        if remaining <= 0:
            st.session_state.page = "results"

    key = f"options_{i}"
    if key not in st.session_state:
        st.session_state[key] = q["options"]
    options = st.session_state[key]
    selected = st.radio("Choose your answer:", options, index=0, key=f"radio_{i}")

    if st.session_state.submitted:
        correct = q["correct_answer"]
        is_correct = selected.strip().lower() == correct.strip().lower()
        st.success("✅ Correct!" if is_correct else f"❌ Wrong! Correct: {correct}")
        st.info(q.get("explanation", "No explanation provided."))
        st.caption(f"Source: {q.get('source', 'Unknown')}")
        if st.button("Next"):
            st.session_state.answers.append(is_correct)
            st.session_state.current += 1
            st.session_state.submitted = False
            if st.session_state.current >= len(questions):
                st.session_state.page = "results"
    else:
        if st.button("Submit"):
            st.session_state.selected_answer = selected
            st.session_state.submitted = True

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    name = st.session_state.player_name.strip()[:5] + "###"
    st.title("🏁 Game Complete!")
    st.markdown(f"**Player:** {name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} sec")

    # Save to leaderboard
    if "saved" not in st.session_state:
        append_to_json(LEADERBOARD_PATH, {
            "name": name,
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.session_state["saved"] = True

    # Certificate
    incorrect_qs = [
        st.session_state.questions[i]
        for i, correct in enumerate(st.session_state.answers)
        if not correct
    ]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    # Leaderboard
    if st.checkbox("Show Leaderboard"):
        st.subheader("🏆 Top 10 Players")
        for i, r in enumerate(get_top_players(), 1):
            st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s")

    # Comment Section
    st.subheader("📝 Leave a comment (visible only to game creator)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment"):
        append_to_json(COMMENTS_PATH, {
            "name": st.session_state.player_name,
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thank you! Comment submitted.")

    # Admin View
    if st.text_input("Admin password:", type="password") == ADMIN_PASSWORD:
        st.subheader("📬 All Comments")
        for c in load_json(COMMENTS_PATH):
            st.markdown(f"**{c.get('name', 'Anon')}** ({c.get('time', '')})")
            st.write(c.get("comment", ""))

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.page = "name"
