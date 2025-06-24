import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

# --- Ensure data persistence files exist ---
def ensure_data_files():
    os.makedirs(".streamlit", exist_ok=True)
    for file_path in [LEADERBOARD_FILE, COMMENTS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

ensure_data_files()

# --- CONFIG ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- UTILITIES ---
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

def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 100, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, h - 140, f"Name: {name}")
    c.drawString(100, h - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, h - 180, f"Duration: {duration} sec")
    c.drawString(100, h - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = h - 240
    if percent < 75:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "Review the following:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q['question']}",
                f"✔ Correct: {q['correct_answer']}",
                f"ℹ {q.get('explanation', '')}"
            ]
            for line in lines:
                for sub in [line[i:i+90] for i in range(0, len(line), 90)]:
                    c.drawString(110, y, sub)
                    y -= 12
                    if y < 100:
                        c.showPage()
                        y = h - 100
            y -= 8
    c.save()
    buf.seek(0)
    return buf

# --- SESSION INIT ---
if "page" not in st.session_state:
    st.session_state.page = "name"

# --- NAME PAGE ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    count = len(load_json(LEADERBOARD_FILE))
    st.markdown(f"**Players so far: {count}**")
    name = st.text_input("Enter your name:")
    if st.button("Continue") and name.strip():
        st.session_state.name = name.strip()
        st.session_state.page = "instructions"

# --- INSTRUCTIONS PAGE ---
elif st.session_state.page == "instructions":
    st.header("📘 Instructions")
    st.markdown("""
- Choose a quiz mode and category  
- Answer questions, learn from feedback  
- 🎯 One click on Submit → shows if correct and explanation  
- ➡️ Then click Next to move on  

**Disclaimer:** This quiz is for learning only. It may include simplifications. It is not legal advice.
""")
    st.session_state.mode = st.selectbox("Select Mode", ["Classic", "Time Attack"])
    all_questions = load_json(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "General") for q in all_questions))
    st.session_state.category = st.selectbox("Select Topic", categories)

    if st.session_state.mode == "Classic":
        st.session_state.num_qs = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)
        st.session_state.num_qs = 100

    if st.button("Start Quiz"):
        pool = [q for q in all_questions if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_qs]
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.feedback = False
        st.session_state.page = "quiz"

# --- QUIZ PAGE ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
            st.stop()
        st.info(f"⏱ Time left: {remaining} sec")

    i = st.session_state.current
    if i >= len(st.session_state.questions):
        st.session_state.page = "results"
        st.stop()

    q = st.session_state.questions[i]
    st.markdown(f"### Question {i+1}")
    st.markdown(q["question"])

    if f"shuffled_{i}" not in st.session_state:
        opts = q["options"][:]
        random.shuffle(opts)
        st.session_state[f"shuffled_{i}"] = opts

    options = st.session_state[f"shuffled_{i}"]
    selected = st.radio("Options:", options, key=f"radio_{i}")

    if not st.session_state.feedback:
        if st.button("Submit"):
            st.session_state.feedback = True
            st.session_state.selected = selected
            correct = q["correct_answer"]
            is_correct = selected.strip().lower() == correct.strip().lower()
            st.session_state.answers.append(is_correct)
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Correct answer: {correct}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.feedback = False

# --- RESULTS PAGE ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    st.success("🎉 Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} sec")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Category:** {st.session_state.category}")

    wrong_qs = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.name, score, total, percent, duration, wrong_qs)
    st.download_button("📄 Download Certificate", cert, "certificate.pdf", "application/pdf")

    # --- Leaderboard ---
    entry = {
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "time": datetime.now().isoformat()
    }
    append_json(LEADERBOARD_FILE, entry)

    if st.checkbox("📊 Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}")

    # --- Comments ---
    st.markdown("### 💬 Leave a comment (only visible to the creator):")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thanks! Your comment is saved.")
    st.caption("🔒 Comments are private and visible only to the game creator.")

    # --- Admin Access ---
    st.markdown("---\n### 🔐 Admin")
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("✅ Access granted.")
        comments = load_json(COMMENTS_FILE)
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
                st.write(c.get("comment", ""))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json", "application/json")
        else:
            st.info("No comments yet.")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
