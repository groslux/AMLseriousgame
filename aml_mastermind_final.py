import streamlit as st
import json
import os
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIG ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- UTILS ---
def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(filepath, entry):
    data = load_json(filepath)
    data.append(entry)
    save_json(filepath, data)

def generate_certificate(name, score, total, percent, duration):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 100, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.save()
    buffer.seek(0)
    return buffer

# --- INIT SESSION ---
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.current = 0

# --- PAGE: NAME ENTRY ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    name = st.text_input("Enter your name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# --- PAGE: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.title("📘 Instructions")
    st.markdown("""
Welcome to the AML Mastermind Quiz!

- Pick a topic and mode
- Click **Submit** once → get feedback
- Click **Submit** again → next question
- Get your certificate at the end

This game is for training only.
""")
    all_qs = load_json(QUESTIONS_FILE)
    st.session_state.mode = st.radio("Select Mode", ["Classic", "Time Attack"])
    categories = sorted(set(q.get("category", "General") for q in all_qs))
    st.session_state.category = st.selectbox("Choose Topic", categories)

    if st.session_state.mode == "Classic":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
        st.session_state.num_questions = 99

    if st.button("Start Quiz"):
        pool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.page = "quiz"
        st.session_state.start_time = time.time()
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.submitted = {}  # Track per-question submission

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    idx = st.session_state.current
    questions = st.session_state.questions

    if idx >= len(questions) or (
        st.session_state.mode == "Time Attack" and
        time.time() - st.session_state.start_time >= st.session_state.time_limit
    ):
        st.session_state.page = "results"
    else:
        q = questions[idx]
        qid = f"q_{idx}"

        if f"shuffled_{qid}" not in st.session_state:
            shuffled = q["options"].copy()
            random.shuffle(shuffled)
            st.session_state[f"shuffled_{qid}"] = shuffled
            st.session_state.submitted[qid] = False

        st.markdown(f"### Question {idx + 1}:")
        st.markdown(f"**{q['question']}**")
        selected = st.radio("Options:", st.session_state[f"shuffled_{qid}"], key=qid)

        if st.button("Submit"):
            if not st.session_state.submitted[qid]:
                # First click → show feedback
                is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
                st.session_state.answers.append(is_correct)
                st.session_state.submitted[qid] = True
                if is_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
                st.info(q.get("explanation", ""))
                st.caption(f"Source: {q.get('source', 'Unknown')}")
            else:
                # Second click → next question
                st.session_state.current += 1

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.title("✅ Quiz Complete")
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration}s")

    # Certificate
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf")

    # Leaderboard
    entry = {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "duration": duration,
        "category": st.session_state.category,
        "timestamp": datetime.now().isoformat()
    }
    append_json(LEADERBOARD_FILE, entry)
    top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x["score"], x["duration"]))[:10]
    st.markdown("### 🏅 Leaderboard (Top 10)")
    for i, r in enumerate(top, 1):
        st.markdown(f"{i}. **{r['name']}** | {r['score']} pts | {r['duration']}s | {r['category']}")

    # Comments
    st.markdown("### 💬 Leave a comment (private)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Comment saved")

    # Admin section
    st.markdown("### 🔐 Admin")
    admin_pw = st.text_input("Admin password", type="password")
    if admin_pw == ADMIN_PASSWORD:
        st.success("Access granted.")
        comments = load_json(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download All Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.page = "name"
