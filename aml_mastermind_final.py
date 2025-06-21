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
COMMENTS_PATH = ".streamlit/comments.json"
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
TIME_OPTIONS = [60, 120, 180]
ADMIN_PASSWORD = "iloveaml2025"

# --- UTILS ---
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

def get_leaderboard():
    return load_json_file(LEADERBOARD_PATH)

def get_player_count():
    return len(get_leaderboard())

def get_top_players():
    return sorted(get_leaderboard(), key=lambda x: (-x['score'], x['duration']))[:10]

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏆 AML Serious Game Certificate")
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
        c.drawString(100, y, "Areas to Improve (based on incorrect answers):")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica", 10)
            for line in [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]:
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

# --- INIT PAGE ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- STATE ---
if "step" not in st.session_state:
    st.session_state.step = "name"

if "answers" not in st.session_state:
    st.session_state.answers = []

questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- NAME INPUT PAGE ---
if st.session_state.step == "name":
    st.title("🕵️ AML Mastermind Deluxe")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have already played: <b>{player_count}</b></div>", unsafe_allow_html=True)
    name = st.text_input("Enter your name to begin:")
    if name:
        st.session_state.player_name = name
        st.session_state.step = "instructions"

    st.stop()

# --- INSTRUCTIONS PAGE ---
if st.session_state.step == "instructions":
    st.title("🎮 Game Instructions")
    st.markdown("""
**🚨 Your Mission:**  
Read the questions, analyze the answers and make the right call.

🔍 Test your AML skills  
💰 Learn AML/CFT facts from Banking, Crypto, and Investment Funds  
📜 Earn your certificate  
🏆 Join the leaderboard!

### How the Game Works:
- Choose Classic or Time Attack mode
- Select a topic: Crypto, Investment Funds, or Banking
- Click "Submit" to validate your answer
- Then click "Next" to move to the next question

📝 **Disclaimer**: This game is for educational purposes only. It may contain simplifications or errors. It is not legal advice.
""")
    if st.button("Start Game"):
        st.session_state.step = "select_mode"
       
    st.stop()

# --- MODE & TOPIC SELECTION ---
if st.session_state.step == "select_mode":
    st.header("🎯 Select Your Mode and Topic")
    mode = st.selectbox("Choose Game Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Choose a Topic", list(grouped.keys()))
    if mode == "Classic Quiz":
        num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)
    if st.button("Begin Quiz"):
        pool = grouped.get(category, [])
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_questions] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.step = "quiz"
      
    st.stop()

# --- QUIZ PAGE ---
if st.session_state.step == "quiz":
    current = st.session_state.current
    total_questions = len(st.session_state.questions)
    if current >= total_questions or (st.session_state.mode == "Time Attack" and time.time() - st.session_state.start_time > st.session_state.time_limit):
        st.session_state.step = "results"
      
    question = st.session_state.questions[current]
    if f"shuffled_options_{current}" not in st.session_state:
        options = question["options"].copy()
        random.shuffle(options)
        st.session_state[f"shuffled_options_{current}"] = options
    st.markdown(f"### Question {current+1}/{total_questions}")
    st.write(question["question"])
    selected = st.radio("Choose an answer:", st.session_state[f"shuffled_options_{current}"], key=f"answer_{current}")
    if "show_feedback" not in st.session_state:
        st.session_state.show_feedback = False
    if st.button("Submit"):
        correct = question["correct_answer"].strip().lower()
        picked = selected.strip().lower()
        is_correct = picked == correct
        st.session_state.answers.append(is_correct)
        st.session_state.last_feedback = {
            "correct": is_correct,
            "answer": question["correct_answer"],
            "explanation": question.get("explanation", "No explanation provided."),
            "source": question.get("source", "Unknown")
        }
        st.session_state.show_feedback = True
    if st.session_state.show_feedback:
        feedback = st.session_state.last_feedback
        st.success("✅ Correct!" if feedback["correct"] else f"❌ Wrong. Correct answer: {feedback['answer']}")
        st.info(feedback["explanation"])
        st.caption(f"Source: {feedback['source']}")
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.show_feedback = False
      
    st.stop()

# --- RESULTS PAGE ---
if st.session_state.step == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    name = st.session_state.player_name.strip()[:5] + "###"
    st.title("📊 Game Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Time Taken:** {duration} seconds")
    append_to_file(LEADERBOARD_PATH, {
        "name": name,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    incorrect_qs = [st.session_state.questions[i] for i, ok in enumerate(st.session_state.answers) if not ok]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("### 🏅 Leaderboard (Top 10)")
    for i, r in enumerate(get_top_players(), 1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']}")

    st.markdown("### 💬 Leave a comment for the game creator")
    comment = st.text_area("Your comment (only visible to the creator):")
    if st.button("Submit Comment"):
        append_to_file(COMMENTS_PATH, {
            "name": st.session_state.player_name,
            "comment": comment,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.success("Thank you! Your comment has been saved.")

    st.markdown("### 🔐 Admin Access to Comments")
    pw = st.text_input("Enter admin password to view comments", type="password")
    if pw == ADMIN_PASSWORD:
        st.subheader("🗂️ All Comments")
        for c in load_json_file(COMMENTS_PATH):
            st.markdown(f"**{c.get('name', '???')}** ({c.get('time', '')})")
            st.markdown(f"➡️ {c.get('comment', '')}")
        st.download_button("📥 Download Comments", json.dumps(load_json_file(COMMENTS_PATH), indent=2), file_name="comments.json")
