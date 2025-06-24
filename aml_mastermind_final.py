import streamlit as st
import json
import os
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# File paths
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# Load/save utilities
def load_json_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_json_file(filepath, entry):
    data = load_json_file(filepath)
    data.append(entry)
    save_json_file(filepath, data)

# Certificate generation
def generate_certificate(name, score, total, percent, duration, category):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(300, 780, "AML Serious Game Certificate of Completion")
    c.setFont("Helvetica", 12)
    c.drawString(100, 740, f"Name: {name}")
    c.drawString(100, 720, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, 700, f"Duration: {duration}s")
    c.drawString(100, 680, f"Category: {category}")
    c.drawString(100, 660, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.save()
    buffer.seek(0)
    return buffer

# Initialize session
if "page" not in st.session_state:
    st.session_state.page = "name"

# --- NAME PAGE ---
if st.session_state.page == "name":
    st.title("🕵️ AML Serious Game for Regulators")
    leaderboard = load_json_file(LEADERBOARD_FILE)
    st.info(f"🧑‍💼 Total players over the past few days: **{len(leaderboard)}**")
    name = st.text_input("Enter your name to begin and click twice on Continue:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# --- INSTRUCTIONS PAGE ---
elif st.session_state.page == "instructions":
    st.title("📋 Instructions")
    st.markdown("""
Welcome to the AML Serious Game for Regulators!

- Choose game mode and topic
- Click Submit once → see feedback
- Click Next → move to next question

Classic mode = fixed number of questions  
Time Attack = beat the clock

A certificate is issued at the end. Top 10 players appear anonymously on the leaderboard.

🔒 This is a training tool and not legal advice.
""")
    st.session_state.mode = st.radio("Select Mode", ["Classic", "Time Attack"])
    all_qs = load_json_file(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "General") for q in all_qs))
    st.session_state.category = st.selectbox("Select Topic", categories)

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
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.submitted = False
        st.session_state.feedback_shown = False
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# --- QUIZ PAGE ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
        else:
            st.markdown(f"⏱️ Time remaining: **{remaining} seconds**")

    current = st.session_state.current
    questions = st.session_state.questions
    q = questions[current]

    if f"options_{current}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{current}"] = opts
        st.session_state[f"selected_{current}"] = None
        st.session_state[f"feedback_{current}"] = False

    st.markdown(f"### Question {current + 1}: {q['question']}")
    selected = st.radio("Options:", st.session_state[f"options_{current}"], key=f"q_{current}")

    if not st.session_state[f"feedback_{current}"]:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state.answers.append(is_correct)
            st.session_state[f"feedback_{current}"] = True
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.current += 1
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- RESULTS PAGE ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.title("✅ Quiz Complete")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration}s")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")

    if not st.session_state.submitted:
        entry = {
            "name": st.session_state.player_name[:5] + "###",
            "score": score,
            "duration": duration,
            "category": st.session_state.category,
            "timestamp": datetime.now().isoformat()
        }
        append_to_json_file(LEADERBOARD_FILE, entry)
        st.session_state.submitted = True

    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, st.session_state.category)
    st.download_button("📄 Download Certificate", cert, file_name="certificate.pdf")

    # Leaderboard
    st.markdown("### 🏆 Leaderboard")
    data = load_json_file(LEADERBOARD_FILE)
    if data:
        # Sort by efficiency: highest correct answers per second
        unique = {entry['timestamp']: entry for entry in data}.values()
        top = sorted(unique, key=lambda x: -(x['score'] / max(x['duration'], 1)))[:10]
        for i, entry in enumerate(top, 1):
            efficiency = round(entry["score"] / max(entry["duration"], 1), 2)
            st.markdown(
                f"{i}. **{entry.get('name', '???')}** | {entry.get('score', 0)} pts"
                f" | {entry.get('duration', '?')}s | Eff.: {efficiency}"
                f" | {entry.get('category', '?')}"
            )
    else:
        st.info("No leaderboard data yet.")

    st.markdown("### 💬 Leave a Comment")
    comment = st.text_area("Private feedback:", key="comment_box_final")
    if st.button("Submit Comment") and comment.strip():
        append_to_json_file(COMMENTS_FILE, {
            "name": st.session_state.get("player_name", "anon")[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Comment saved.")

    st.markdown("### 🔐 Admin Login")
    pw = st.text_input("Admin Password", type="password")
    if pw == ADMIN_PASSWORD:
        comments = load_json_file(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "name"
