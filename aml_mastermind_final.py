import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# Constants
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# JSON helper functions
def load_json(path, default=[]):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json(path, entry):
    data = load_json(path)
    data.append(entry)
    save_json(path, data)

# Certificate generator
def generate_certificate(name, score, total, percent, duration, wrong_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 80, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(80, height - 120, f"Name: {name}")
    c.drawString(80, height - 140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(80, height - 160, f"Duration: {duration} sec")
    c.drawString(80, height - 180, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 220
    if wrong_qs:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(80, y, "Review these questions:")
        y -= 20
        c.setFont("Helvetica", 10)
        for q in wrong_qs:
            c.drawString(90, y, f"Q: {q['question']}")
            y -= 12
            c.drawString(100, y, f"✔ Correct: {q['correct_answer']}")
            y -= 12
            c.drawString(100, y, f"ℹ {q.get('explanation', '')}")
            y -= 30
            if y < 100:
                c.showPage()
                y = height - 100
    c.save()
    buffer.seek(0)
    return buffer

# Initialize session
if "page" not in st.session_state:
    st.session_state.page = "name"
if "answers" not in st.session_state:
    st.session_state.answers = []
if "current_q" not in st.session_state:
    st.session_state.current_q = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False

# Page: Name
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind")
    st.markdown("### Enter your name to begin")
    player_name = st.text_input("Your name")
    if st.button("Continue") and player_name.strip():
        st.session_state.player_name = player_name.strip()
        st.session_state.page = "instructions"

# Page: Instructions + setup
elif st.session_state.page == "instructions":
    st.title("📘 Instructions")
    st.markdown("""
- One click on `Submit` = shows correct/wrong  
- Second click on `Submit` = goes to next question  
- At the end: 🎓 certificate, 🏅 leaderboard, 🗣️ comment box
    """)
    data = load_json(QUESTIONS_FILE)
    categories = sorted(set(q["category"] for q in data))
    category = st.selectbox("Select topic", categories)
    num_questions = st.slider("Number of questions", 5, 20, 10)
    if st.button("Start Quiz"):
        questions = [q for q in data if q["category"] == category]
        random.shuffle(questions)
        st.session_state.questions = questions[:num_questions]
        st.session_state.category = category
        st.session_state.num_questions = num_questions
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# Page: Quiz
elif st.session_state.page == "quiz":
    q_idx = st.session_state.current_q
    total = len(st.session_state.questions)
    if q_idx >= total:
        st.session_state.page = "results"
        st.experimental_rerun()

    q = st.session_state.questions[q_idx]
    st.subheader(f"Question {q_idx + 1} of {total}")
    st.write(q["question"])

    key = f"options_{q_idx}"
    if key not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[key] = opts
    selected = st.radio("Choose one:", st.session_state[key], key=f"select_{q_idx}")

    if st.button("Submit"):
        if not st.session_state.feedback_shown:
            st.session_state.selected = selected
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(is_correct)
            st.session_state.feedback_shown = True
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
        else:
            st.session_state.current_q += 1
            st.session_state.feedback_shown = False
            st.experimental_rerun()

# Page: Results
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = int((score / total) * 100)
    duration = int(time.time() - st.session_state.start_time)
    wrong_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]

    st.title("✅ Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, wrong_qs)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf", mime="application/pdf")

    # Save best score only
    all_scores = load_json(LEADERBOARD_FILE)
    anonymized_name = st.session_state.player_name[:5] + "###"
    filtered = [s for s in all_scores if s["name"] != anonymized_name]
    filtered.append({
        "name": anonymized_name,
        "score": score,
        "duration": duration,
        "category": st.session_state.category,
        "timestamp": datetime.now().isoformat()
    })
    save_json(LEADERBOARD_FILE, filtered)

    if st.checkbox("🏅 Show Leaderboard"):
        lb = load_json(LEADERBOARD_FILE)
        best_per_user = {}
        for entry in lb:
            name = entry.get("name", "Anon###")
            current = best_per_user.get(name)
            if not current or entry["score"] > current["score"] or (
                entry["score"] == current["score"] and entry["duration"] < current["duration"]
            ):
                best_per_user[name] = entry
        top = sorted(best_per_user.values(), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, entry in enumerate(top, 1):
            st.markdown(f"{i}. **{entry['name']}** | {entry['score']} pts | {entry['duration']}s | {entry.get('category', '')}")

    st.markdown("---")
    st.markdown("### 🗣️ Leave a comment (visible only to the creator)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_to_json(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you! Your comment has been submitted.")
    st.caption("Comments are private and only visible to the game creator.")

    st.markdown("### 🔐 Admin Access")
    password = st.text_input("Password", type="password")
    if password == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        st.success("Access granted")
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name', '???')}** ({c.get('time', '')}):")
                st.write(c.get("comment", ""))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")
        else:
            st.info("No comments yet.")

    if st.button("🔄 Play Again"):
        st.session_state.clear()
        st.experimental_rerun()
