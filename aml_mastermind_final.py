import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

# --- FILE PATHS ---
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
QUESTIONS_FILE = "questions_cleaned.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- INIT STATE ---
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.current = 0
    st.session_state.feedback = False
    st.session_state.selected = None
    st.session_state.questions = []
    st.session_state.start_time = None
    st.session_state.mode = "Classic Quiz"
    st.session_state.category = None

# --- UTILS ---
def load_json(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

def append_json(path, entry):
    data = load_json(path)
    data.append(entry)
    save_json(path, data)

def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 80, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 120, f"Name: {name}")
    c.drawString(50, height - 140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(50, height - 160, f"Duration: {duration} seconds")
    c.drawString(50, height - 180, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 220
    if incorrect_qs:
        c.drawString(50, y, "Topics to review:")
        for q in incorrect_qs:
            y -= 40
            c.setFont("Helvetica-Bold", 10)
            c.drawString(60, y, f"Q: {q['question'][:80]}")
            y -= 12
            c.setFont("Helvetica", 10)
            c.drawString(70, y, f"✔ Correct: {q['correct_answer']}")
            y -= 12
            c.drawString(70, y, f"ℹ {q.get('explanation', 'No explanation')}")
            if y < 100:
                c.showPage()
                y = height - 100
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGE: NAME ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    count = len(load_json(LEADERBOARD_FILE))
    st.markdown(f"**Players so far:** {count}")
    name = st.text_input("Enter your name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# --- PAGE: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.header("📚 How to Play")
    st.markdown("""
- Choose **Classic** or **Time Attack** mode  
- Pick a topic (Crypto, Funds, Banking)  
- Answer questions, learn from mistakes  
- Get your 🎓 certificate + appear on 🏅 leaderboard  
- Leave a private comment at the end

🛑 *Disclaimer:* This quiz is for educational purposes only and may contain simplifications. It is not legal advice.
    """)
    st.session_state.mode = st.selectbox("Select Mode", ["Classic Quiz", "Time Attack"])
    questions = load_json(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "Other") for q in questions))
    st.session_state.category = st.selectbox("Select Topic", categories)

    if st.session_state.mode == "Classic Quiz":
        num_q = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
        num_q = 99

    if st.button("Start Quiz"):
        pool = [q for q in questions if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:num_q]
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.feedback = False
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        left = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if left <= 0:
            st.session_state.page = "results"

    i = st.session_state.current
    if i >= len(st.session_state.questions):
        st.session_state.page = "results"
        st.experimental_rerun()

    q = st.session_state.questions[i]
    st.subheader(f"Question {i + 1}")
    st.write(q["question"])

    if f"shuffled_{i}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"shuffled_{i}"] = opts

    st.session_state.selected = st.radio("Options:", st.session_state[f"shuffled_{i}"], key=f"radio_{i}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = st.session_state.selected.strip().lower()
            is_correct = picked == correct
            st.session_state.feedback = True
            st.session_state.answers.append(is_correct)
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.feedback = False
            st.experimental_rerun()

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.header("✅ Quiz Complete")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} seconds")

    incorrect_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf")

    append_json(LEADERBOARD_FILE, {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "total": total,
        "duration": duration,
        "percent": percent,
        "timestamp": datetime.now().isoformat(),
        "mode": st.session_state.mode,
        "category": st.session_state.category,
    })

    st.subheader("🏅 Leaderboard (Top 10)")
    top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x["score"], x["duration"]))[:10]
    for idx, r in enumerate(top, 1):
        st.markdown(f"{idx}. **{r['name']}** | {r['score']}/{r['total']} in {r['duration']}s | {r['category']}")

    st.markdown("### 🗣 Leave a private comment (not public):")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thanks! Comment received.")

    st.caption("Comments are visible only to the game creator.")

    st.markdown("### 🔐 Admin Panel")
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_json(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name', '?')}** ({c.get('time', '')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
