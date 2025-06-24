import streamlit as st
import json
import random
import time
import os
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- File paths ---
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
QUESTIONS_FILE = "questions_cleaned.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- Load/save helpers ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, item):
    data = load_json(path)
    data.append(item)
    save_json(path, data)

# --- Certificate ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height-100, "🎓 AML Quiz Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height-140, f"Name: {name}")
    c.drawString(100, height-160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height-180, f"Duration: {duration} seconds")
    y = height-220
    if incorrect_qs:
        c.drawString(100, y, "Topics to review:")
        y -= 20
        cats = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        for cat in cats:
            c.drawString(120, y, f"- {cat}")
            y -= 15
    else:
        c.drawString(100, y, "Excellent work! 🏆")
    c.save()
    buffer.seek(0)
    return buffer

# --- Page config ---
st.set_page_config("AML Mastermind", layout="centered")

# --- State init ---
for key in ["page", "answers", "current", "start_time", "submitted", "feedback"]:
    if key not in st.session_state:
        st.session_state[key] = None
if st.session_state.page is None:
    st.session_state.page = "name"

# --- Name input page ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind Quiz")
    st.markdown("Enter your name to begin:")
    name = st.text_input("Name:")
    if st.button("Start"):
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.page = "setup"

# --- Game setup page ---
elif st.session_state.page == "setup":
    st.header("🧠 Game Setup")
    st.markdown("Choose your game mode and topic.")
    all_qs = load_json(QUESTIONS_FILE)
    st.session_state.mode = st.selectbox("Mode", ["Classic", "Time Attack"])
    cats = sorted(set(q.get("category", "Other") for q in all_qs))
    st.session_state.category = st.selectbox("Category", cats)
    if st.session_state.mode == "Classic":
        n = st.slider("Number of questions", 5, 20, 10)
        st.session_state.num_questions = n
        st.session_state.time_limit = None
    else:
        sec = st.selectbox("Time limit (seconds)", [60, 120, 180])
        st.session_state.time_limit = sec
        st.session_state.num_questions = 99
    if st.button("Launch Quiz"):
        qpool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(qpool)
        st.session_state.questions = qpool[:st.session_state.num_questions]
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.page = "quiz"
        st.session_state.start_time = time.time()
        st.session_state.submitted = False

# --- Quiz page ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        elapsed = time.time() - st.session_state.start_time
        left = st.session_state.time_limit - int(elapsed)
        if left <= 0:
            st.session_state.page = "results"
        st.markdown(f"⏱️ Time left: {left} seconds")

    idx = st.session_state.current
    q = st.session_state.questions[idx]
    st.markdown(f"### Question {idx+1}")
    st.markdown(q["question"])
    if f"options_{idx}" not in st.session_state:
        shuffled = q["options"].copy()
        random.shuffle(shuffled)
        st.session_state[f"options_{idx}"] = shuffled
    options = st.session_state[f"options_{idx}"]
    selected = st.radio("Your answer:", options, key=f"answer_{idx}")

    if not st.session_state.submitted:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            chosen = selected.strip().lower()
            is_correct = chosen == correct
            st.session_state.answers.append(is_correct)
            st.session_state.feedback = {
                "is_correct": is_correct,
                "explanation": q.get("explanation", "No explanation."),
                "source": q.get("source", "Unknown"),
                "correct_answer": q["correct_answer"]
            }
            st.session_state.submitted = True
    else:
        fb = st.session_state.feedback
        if fb["is_correct"]:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ Wrong. Correct answer: {fb['correct_answer']}")
        st.info(fb["explanation"])
        st.caption(f"Source: {fb['source']}")
        if st.button("Submit"):
            st.session_state.submitted = False
            st.session_state.feedback = None
            st.session_state.current += 1
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- Results page ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    st.title("🎉 Quiz Complete")
    st.write(f"Player: {st.session_state.player_name}")
    st.write(f"Score: {score}/{total} ({percent}%)")
    st.write(f"Duration: {duration} seconds")
    incorrect_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf")

    entry = {
        "name": st.session_state.player_name[:5] + "###",
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
        top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['category']}")

    st.markdown("### 🗣️ Feedback")
    comment = st.text_area("Leave a private comment:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thanks for your feedback!")

    st.caption("Comments are private and only visible to the game creator.")

    st.markdown("### 🔐 Admin")
    pw = st.text_input("Password:", type="password")
    if pw == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        st.success("Access granted.")
        if comments:
            for c in comments:
                st.markdown(f"**{c['name']}** ({c['time']}):")
                st.write(c["comment"])
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")
        else:
            st.info("No comments yet.")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
