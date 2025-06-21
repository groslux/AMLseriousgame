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

# --- CONFIGURATION ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]
ADMIN_PASSWORD = "iloveaml2025"

# --- PAGE SETUP ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")

# --- FUNCTIONS: FILE STORAGE ---
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

# --- FUNCTIONS: LEADERBOARD / COMMENTS ---
def get_leaderboard():
    return load_json(LEADERBOARD_PATH)

def append_leaderboard(record):
    append_to_json(record, LEADERBOARD_PATH)

def get_top_players():
    return sorted(get_leaderboard(), key=lambda x: (-x["score"], x["duration"]))[:10]

def get_player_count():
    return len(get_leaderboard())

def save_comment(name, comment):
    if not comment.strip():
        return
    record = {
        "name": name.strip()[:5] + "###",
        "comment": comment.strip(),
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    append_to_json(record, COMMENTS_PATH)

# --- FUNCTIONS: CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏅 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Congratulations! Excellent performance.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🧠 Areas to Improve:")
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

# --- FUNCTIONS: QUESTIONS ---
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

# --- STATE INITIALIZATION ---
def init_state():
    keys = {
        "step": "name",
        "player_name": "",
        "mode": "",
        "category": "",
        "questions": [],
        "current": 0,
        "answers": [],
        "submitted": False,
        "start_time": None,
        "time_limit": None,
        "game_ended": False
    }
    for k, v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

questions_data = load_questions()
grouped_questions = group_by_category(questions_data)

# --- PAGE 1: NAME INPUT ---
if st.session_state.step == "name":
    st.title("🔐 AML Mastermind Deluxe")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>🎮 Players who have already played: <b>{get_player_count()}</b></div>", unsafe_allow_html=True)
    st.text_input("Enter your name to begin:", key="player_name")
    if st.button("Continue"):
        if st.session_state.player_name.strip():
            st.session_state.step = "instructions"
        else:
            st.warning("Please enter your name.")

# --- PAGE 2: INSTRUCTIONS & SETUP ---
elif st.session_state.step == "instructions":
    st.title("🕵️ Welcome to the AML Serious Game for Supervisors")
    st.markdown("""
**🚨 Your Mission:**  
Answer AML questions accurately and quickly. Your performance will be scored.

🔍 Topics: Banking, Crypto, Investment Funds  
📜 Certificate awarded with feedback  
🏆 Join the leaderboard  

### ⚠️ Disclaimer
This game is for educational purposes only. There may be simplifications and errors. This is not AML advice.

---

""")
    mode = st.selectbox("Choose your game mode:", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Choose a topic:", list(grouped_questions.keys()))
    if mode == "Classic Quiz":
        num_qs = st.slider("How many questions?", 5, 30, 10)
    else:
        time_limit = st.selectbox("Time limit (seconds):", TIME_OPTIONS)

    if st.button("Start Game"):
        pool = grouped_questions.get(category, [])[:]
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_qs] if mode == "Classic Quiz" else pool
        st.session_state.time_limit = time_limit if mode == "Time Attack" else None
        st.session_state.start_time = time.time()
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.submitted = False
        st.session_state.step = "quiz"

# --- PAGE 3: QUIZ ---
elif st.session_state.step == "quiz":
    current = st.session_state.current
    questions = st.session_state.questions
    total = len(questions)

    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        st.markdown(f"⏱️ Time Left: **{remaining} seconds**")
        if remaining <= 0:
            st.session_state.step = "results"

    if current < total:
        q = questions[current]
        if f"options_{current}" not in st.session_state:
            options = q["options"][:]
            random.shuffle(options)
            st.session_state[f"options_{current}"] = options
        options = st.session_state[f"options_{current}"]

        st.markdown(f"### Question {current + 1} of {total}")
        st.markdown(q["question"])
        choice = st.radio("Choose your answer:", options, key=f"q_{current}")

        if not st.session_state.submitted:
            if st.button("Submit"):
                correct = q["correct_answer"].strip().lower()
                picked = choice.strip().lower()
                st.session_state.answers.append(picked == correct)
                st.session_state.submitted = True
                st.success("✅ Correct!" if picked == correct else f"❌ Wrong! Correct answer: {q['correct_answer']}")
                st.info(q.get("explanation", "No explanation provided."))
                st.caption(f"Source: {q.get('source', 'Unknown')}")
        else:
            if st.button("Next"):
                st.session_state.current += 1
                st.session_state.submitted = False
    else:
        st.session_state.step = "results"

# --- PAGE 4: RESULTS ---
elif st.session_state.step == "results":
    st.title("✅ Game Complete!")
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)

    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} seconds")

    append_leaderboard({
        "name": st.session_state.player_name.strip()[:5] + "###",
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    incorrect_qs = [st.session_state.questions[i] for i, correct in enumerate(st.session_state.answers) if not correct]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download your certificate", data=cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("---")
    st.markdown("### 🏆 Leaderboard")
    for i, entry in enumerate(get_top_players(), 1):
        st.markdown(f"{i}. {entry['name']} | {entry['score']}/{entry['total']} | {entry['duration']}s")

    st.markdown("---")
    st.markdown("### 💬 Leave a private comment (visible only to the game creator):")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment"):
        save_comment(st.session_state.player_name, comment)
        st.success("Thank you! Your comment has been saved.")

    st.markdown("---")
    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Enter admin password to view comments", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("✅ Admin access granted")
        for c in load_json(COMMENTS_PATH):
            st.markdown(f"**{c['name']}** ({c['time']})")
            st.write(c['comment'])
        st.download_button("⬇️ Download comments", json.dumps(load_json(COMMENTS_PATH), indent=2), "comments.json", mime="application/json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()

st.markdown("---")
st.caption("🔍 Designed for AML training – GROS – Luxembourg – FATF, IMF, IOSCO sources.")
