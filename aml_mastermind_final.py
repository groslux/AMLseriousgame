import streamlit as st
import json
import random
import time
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- Paths ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
QUESTION_FILE = "questions_cleaned.json"
PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- Utils: Local storage ---
def load_json_file(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_file(path, record):
    data = load_json_file(path)
    data.append(record)
    save_json_file(path, data)

# --- Certificate ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, h - 80, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(80, h - 120, f"Name: {name}")
    c.drawString(80, h - 140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(80, h - 160, f"Duration: {duration} seconds")
    c.drawString(80, h - 180, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = h - 220
    if percent >= 75:
        c.drawString(80, y, "🎉 Excellent performance!")
    else:
        c.drawString(80, y, "🛠 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question','')}",
                f"✔ Correct: {q.get('correct_answer','')}",
                f"ℹ Explanation: {q.get('explanation','')}"
            ]
            for line in lines:
                for part in [line[i:i+90] for i in range(0, len(line), 90)]:
                    c.drawString(100, y, part)
                    y -= 12
                    if y < 100:
                        c.showPage()
                        y = h - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- Load & group questions ---
@st.cache_data
def load_questions():
    with open(QUESTION_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

questions_by_category = load_questions()
player_count = len(load_json_file(LEADERBOARD_PATH))

# --- Init Session State ---
def init_state():
    defaults = {
        "step": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "answers": [],
        "start_time": None,
        "current": 0,
        "submitted": False,
        "selected_answer": None,
        "leaderboard_saved": False,
        "time_limit": None,
        "admin": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
init_state()

# --- Page: Name Input ---
if st.session_state.step == "name":
    st.title("🕵️ AML Mastermind Deluxe")
    st.markdown(f"Players who have already played: **{player_count}**")
    name = st.text_input("Enter your name to begin:")
    if st.button("Continue"):
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.step = "intro"

# --- Page: Instructions ---
elif st.session_state.step == "intro":
    st.title("🎯 Instructions")
    st.markdown("""
    **Your Mission**  
    - Test your AML knowledge  
    - Topics: 🏦 Banking, 💸 Crypto, 📊 Investment Funds  
    - Get a 🧾 certificate and join the 🏆 leaderboard!

    ### Disclaimer:
    This game is for training only. There may be mistakes or simplifications. No legal advice.

    You will:
    - Choose mode (Classic or Time Attack)
    - Select a topic
    - Answer questions (click Submit then Next)
    """)
    if st.button("Start"):
        st.session_state.step = "config"

# --- Page: Configuration ---
elif st.session_state.step == "config":
    st.title("🎮 Choose Your Game")
    mode = st.selectbox("Select Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Select Topic", list(questions_by_category.keys()))
    if mode == "Classic Quiz":
        num_qs = st.slider("Number of Questions", 5, 30, 10)
        time_limit = None
    else:
        num_qs = None
        time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Launch Quiz"):
        pool = questions_by_category[category][:]
        random.shuffle(pool)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = pool[:num_qs] if num_qs else pool
        st.session_state.start_time = time.time()
        st.session_state.time_limit = time_limit
        st.session_state.step = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []

# --- Page: Quiz ---
elif st.session_state.step == "quiz":
    idx = st.session_state.current
    total = len(st.session_state.questions)

    if st.session_state.mode == "Time Attack":
        elapsed = int(time.time() - st.session_state.start_time)
        remaining = st.session_state.time_limit - elapsed
        st.markdown(f"⏱ Time Left: **{remaining} sec**")
        if remaining <= 0:
            st.session_state.step = "result"
            st.stop()

    q = st.session_state.questions[idx]
    st.markdown(f"### Question {idx + 1} / {total}")
    st.write(q["question"])

    if f"options_{idx}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{idx}"] = opts
    options = st.session_state[f"options_{idx}"]

    selected = st.radio("Your answer:", options, index=0, key=f"selected_{idx}")
    if not st.session_state.submitted:
        if st.button("Submit"):
            st.session_state.selected_answer = selected
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.session_state.submitted = True
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation"))
            st.caption(f"📚 Source: {q.get('source','Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.submitted = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.step = "result"

# --- Page: Results ---
elif st.session_state.step == "result":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.title("🏁 Game Complete")
    st.markdown(f"""
    **Player:** {st.session_state.player_name}  
    **Mode:** {st.session_state.mode}  
    **Topic:** {st.session_state.category}  
    **Score:** {score}/{total} ({percent}%)  
    **Time:** {duration}s  
    **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """)

    if not st.session_state.leaderboard_saved:
        append_to_file(LEADERBOARD_PATH, {
            "name": st.session_state.player_name[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.session_state.leaderboard_saved = True

    incorrect_qs = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("### 🏆 Leaderboard")
    top = sorted(load_json_file(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, r in enumerate(top, start=1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s")

    st.markdown("### 💬 Leave a comment (only visible to the game creator)")
    comment = st.text_area("Your comment:")
    if st.button("Submit Comment"):
        if comment.strip():
            append_to_file(COMMENTS_PATH, {
                "name": st.session_state.player_name[:5] + "###",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "comment": comment.strip()
            })
            st.success("✅ Comment submitted!")

    st.markdown("---")
    st.button("🔁 Play Again", on_click=lambda: st.session_state.clear())

# --- Page: Admin ---
if st.sidebar.text_input("Admin Password", type="password") == PASSWORD:
    st.sidebar.success("🔓 Admin Access")
    st.markdown("## 🛠 Admin: Player Comments")
    comments = load_json_file(COMMENTS_PATH)
    if not comments:
        st.info("No comments yet.")
    else:
        for c in comments:
            st.markdown(f"**{c['name']}** ({c['time']})")
            st.markdown(f"> {c['comment']}")
            st.markdown("---")
