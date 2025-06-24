import streamlit as st
import json
import os
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- UTILS ---
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

def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🎓 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "Congratulations! 🏆 You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "Areas to Improve:")
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
    c.save()
    buffer.seek(0)
    return buffer

# --- STREAMLIT SETUP ---
st.set_page_config("AML Mastermind", layout="centered")

# --- SESSION INIT ---
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.current = 0
    st.session_state.feedback = False
    st.session_state.submitted = False

# --- PAGE 1: ENTER NAME ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind Quiz")
    count = len(load_json_file(LEADERBOARD_FILE))
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players so far: <b>{count}</b></div>", unsafe_allow_html=True)
    name = st.text_input("Your name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.markdown("## 📚 How the Game Works")
    st.markdown("""
- Choose Classic or Time Attack mode  
- Select a topic: Crypto, Investment Funds, or Banking  
- One click on `Submit`: shows if answer is correct  
- One more click on `Submit`: moves to next question  
At the end:  
- 🎓 Receive a certificate  
- 🏅 See your leaderboard rank  
- 🗣️ Leave a private comment to the game creator
""")
    st.session_state.mode = st.radio("Select Mode", ["Classic", "Time Attack"])
    all_qs = load_json_file(QUESTIONS_FILE)
    categories = sorted(set(q.get("category", "General") for q in all_qs))
    st.session_state.category = st.selectbox("Select Topic", categories)

    if st.session_state.mode == "Classic":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)
        st.session_state.num_questions = 99

    if st.button("Start Quiz"):
        pool = [q for q in all_qs if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.feedback = False

# --- PAGE 3: QUIZ ---
# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    current = st.session_state.current
    questions = st.session_state.questions
    total = len(questions)

    if current >= total:
        st.session_state.page = "results"
    else:
        q = questions[current]

        # Display question text
        st.subheader(f"❓ Question {current + 1} of {total}")
        st.markdown(f"**{q['question']}**")

        # Shuffle options once
        if f"options_{current}" not in st.session_state:
            opts = q["options"].copy()
            random.shuffle(opts)
            st.session_state[f"options_{current}"] = opts
            st.session_state[f"selected_{current}"] = None
            st.session_state[f"submitted_{current}"] = False

        # Show options
        options = st.session_state[f"options_{current}"]
        selected = st.radio("Choose your answer:", options, key=f"radio_{current}")

        # Submit button
        if st.button("Submit"):
            if not st.session_state[f"submitted_{current}"]:
                # First click → show feedback
                st.session_state[f"selected_{current}"] = selected
                correct = q["correct_answer"].strip().lower()
                picked = selected.strip().lower()
                is_correct = picked == correct
                st.session_state.answers.append(is_correct)
                st.session_state[f"submitted_{current}"] = True

                if is_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. Correct answer: {q['correct_answer']}")
                st.info(q.get("explanation", "No explanation provided."))
                st.caption(f"Source: {q.get('source', 'Unknown')}")

            else:
                # Second click → move to next question
                st.session_state.current += 1
                st.session_state[f"options_{current+1}"] = None  # force reload of next options
                st.session_state.page = "quiz"



# --- PAGE 4: RESULTS ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    incorrect_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]

    st.title("✅ Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")
    st.markdown(f"**Mode:** {st.session_state.mode} | **Category:** {st.session_state.category}")

    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", cert, file_name="certificate.pdf", mime="application/pdf")

    if not st.session_state.submitted:
        append_to_json_file(LEADERBOARD_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "score": score,
            "duration": duration,
            "category": st.session_state.category,
            "timestamp": datetime.now().isoformat()
        })
        st.session_state.submitted = True

    st.markdown("---\n### 🏆 Leaderboard")
    data = load_json_file(LEADERBOARD_FILE)
    top = sorted(data, key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, entry in enumerate(top, 1):
        st.markdown(f"{i}. **{entry.get('name', '???')}** | {entry.get('score', 0)} pts | {entry.get('duration', '?')}s | {entry.get('category', '?')}")

    st.markdown("---\n### 🗣️ Leave a private comment:")
    comment = st.text_area("Your comment:")
    if st.button("Submit Comment") and comment.strip():
        append_to_json_file(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you! Your comment has been submitted.")

    st.markdown("### 🔐 Admin Section")
    pw = st.text_input("Admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_json_file(COMMENTS_FILE)
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name', '???')}** ({c.get('time', '')}):")
                st.write(c.get("comment", ""))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json", "application/json")
        else:
            st.info("No comments yet.")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.page = "name"
