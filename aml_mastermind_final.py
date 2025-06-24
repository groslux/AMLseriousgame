import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import os

# --- CONFIG ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- INIT ---
st.set_page_config("AML Quiz Game", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "name"

def load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def add_to_json(filepath, new_entry):
    data = load_json(filepath)
    data.append(new_entry)
    save_json(filepath, data)

def generate_certificate(name, score, total, percent, duration, wrong_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w / 2, h - 100, "🎓 AML Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(80, h - 140, f"Name: {name}")
    c.drawString(80, h - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(80, h - 180, f"Duration: {duration} sec")
    c.drawString(80, h - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = h - 240
    if percent >= 75:
        c.drawString(80, y, "Well done! ✅")
    else:
        c.drawString(80, y, "Review these topics:")
        y -= 20
        for q in wrong_qs:
            lines = [
                f"Q: {q['question']}",
                f"✔ {q['correct_answer']}",
                f"ℹ {q.get('explanation', '')}"
            ]
            for line in lines:
                for chunk in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(100, y, chunk)
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = h - 80
            y -= 8
    c.save()
    buffer.seek(0)
    return buffer

# --- PAGES ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    player_count = len(load_json(LEADERBOARD_FILE))
    st.markdown(f"**Players so far: {player_count}**")
    name = st.text_input("Enter your name to begin:")
    if st.button("Start"):
        if name.strip():
            st.session_state.name = name.strip()
            st.session_state.page = "instructions"
            st.session_state.answers = []
            st.session_state.start_time = None

elif st.session_state.page == "instructions":
    st.title("📚 How to Play")
    st.markdown("""
- Choose game mode and topic  
- Submit your answer, see feedback, click Next  
- Get a certificate, leaderboard rank, and leave feedback!

📝 **Disclaimer**: This quiz is for training only. No legal advice. May contain simplifications.
    """)
    st.session_state.mode = st.selectbox("Choose Mode", ["Classic", "Time Attack"])
    all_qs = load_json(QUESTIONS_FILE)
    categories = sorted({q.get("category", "Other") for q in all_qs})
    st.session_state.category = st.selectbox("Select Topic", categories)
    if st.session_state.mode == "Classic":
        st.session_state.q_limit = st.slider("Questions:", 5, 30, 10)
        st.session_state.t_limit = None
    else:
        st.session_state.t_limit = st.selectbox("Time Limit (sec)", [60, 120, 180])
        st.session_state.q_limit = 99
    if st.button("Launch Quiz"):
        pool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.q_limit]
        st.session_state.current = 0
        st.session_state.page = "quiz"
        st.session_state.start_time = time.time()
        st.session_state.feedback = False

elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        left = st.session_state.t_limit - int(time.time() - st.session_state.start_time)
        if left <= 0:
            st.session_state.page = "results"
    q_idx = st.session_state.current
    question = st.session_state.questions[q_idx]
    st.markdown(f"### Q{q_idx + 1}: {question['question']}")
    key = f"q_{q_idx}"
    if f"options_{q_idx}" not in st.session_state:
        opt = question["options"].copy()
        random.shuffle(opt)
        st.session_state[f"options_{q_idx}"] = opt
    options = st.session_state[f"options_{q_idx}"]
    choice = st.radio("Your answer:", options, key=key)
    
    if not st.session_state.feedback:
        if st.button("Submit"):
            st.session_state.feedback = True
            st.session_state.selected = choice
            correct = question["correct_answer"].strip().lower()
            picked = choice.strip().lower()
            st.session_state.correct = (correct == picked)
            if st.session_state.correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Correct answer: {question['correct_answer']}")
            st.info(question.get("explanation", ""))
            st.caption(f"📚 Source: {question.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.answers.append(st.session_state.correct)
            st.session_state.feedback = False
            st.session_state.current += 1
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

elif st.session_state.page == "results":
    st.title("✅ Quiz Complete")
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.markdown(f"**{st.session_state.name}** | Score: {score}/{total} ({percent}%) | Time: {duration} sec")
    
    wrong = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]
    cert = generate_certificate(st.session_state.name, score, total, percent, duration, wrong)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf")

    add_to_json(LEADERBOARD_FILE, {
        "name": st.session_state.name[:5] + "###",
        "score": score, "total": total, "percent": percent,
        "duration": duration, "category": st.session_state.category,
        "mode": st.session_state.mode, "time": datetime.now().isoformat()
    })

    if st.checkbox("🏆 View Leaderboard"):
        top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['category']}")

    st.markdown("---")
    st.markdown("### 🗣️ Leave a comment (private):")
    comment = st.text_area("Your comment:")
    if st.button("Send Comment") and comment.strip():
        add_to_json(COMMENTS_FILE, {
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Comment submitted. Thank you!")

    st.caption("Only visible to the game creator.")

    st.markdown("### 🔐 Admin")
    pw = st.text_input("Enter password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_json(COMMENTS_FILE)
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
                st.write(c.get("comment"))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json", "application/json")
        else:
            st.info("No comments yet.")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
