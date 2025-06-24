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

# --- FILE PATHS ---
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
QUESTIONS_FILE = "questions_cleaned.json"
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
        c.drawString(100, y, "Areas to Improve (based on incorrect answers):")
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
# --- STREAMLIT SETUP ---
st.set_page_config("AML Mastermind", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "name"

# --- PAGE 1: ENTER NAME ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind Quiz")
    count = len(load_json_file(LEADERBOARD_FILE))
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players so far: <b>{count}</b></div>", unsafe_allow_html=True)
    st.markdown("## Enter your name to begin")
    name = st.text_input("Your name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.page = "instructions"
        st.session_state.answers = []
        st.session_state.start_time = None

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.markdown("## 📚 How the Game Works")
    st.markdown("""
- Choose Classic or Time Attack mode  
- Select a topic: Crypto, Investment Funds, or Banking  
- Answer questions and learn from explanations  
- Click `Submit` once → see feedback → Click `Next` to move on

### 🔒 Disclaimer:
This quiz is for training purposes only. It may contain approximations or simplifications. It is not legal advice.

At the end:  
- 🎓 Receive a certificate  
- 🏅 See your leaderboard rank  
- 🗣️ Leave a private comment to the game creator
    """)
    st.session_state.mode = st.selectbox("Select mode", ["Classic Quiz", "Time Attack"])
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        all_questions = json.load(f)
    categories = sorted(set(q.get("category", "Other") for q in all_questions))
    st.session_state.category = st.selectbox("Select category", categories)

    if st.session_state.mode == "Classic Quiz":
        st.session_state.num_questions = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)
        st.session_state.num_questions = 99  # large number to allow time-based limit

    if st.button("Start Quiz"):
        pool = [q for q in all_questions if q.get("category") == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.num_questions]
        st.session_state.page = "quiz"
        st.session_state.current = 0
        st.session_state.start_time = time.time()
        st.session_state.feedback_displayed = False
# --- PAGE 3: QUIZ ---
elif st.session_state.page == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.page = "results"
    st.markdown(f"### Question {st.session_state.current + 1}")
    q = st.session_state.questions[st.session_state.current]
        if "question" not in q:
        st.error("❌ Error: Question text missing for this entry.")
        st.write(q)
        st.stop()

    
    if f"options_{st.session_state.current}" not in st.session_state:
        shuffled = q["options"].copy()
        random.shuffle(shuffled)
        st.session_state[f"options_{st.session_state.current}"] = shuffled
    
    options = st.session_state[f"options_{st.session_state.current}"]
    selected = st.radio("Choose your answer:", options, key=f"q_{st.session_state.current}")

    if not st.session_state.get("feedback_displayed", False):
        if st.button("Submit"):
            st.session_state["selected_answer"] = selected
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            st.session_state["is_correct"] = picked == correct
            st.session_state.feedback_displayed = True
            if st.session_state["is_correct"]:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Wrong. Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation provided."))
            st.caption(f"Source: {q.get('source', 'Unknown')}")

    elif st.button("Next"):
        st.session_state.answers.append(st.session_state["is_correct"])
        st.session_state.feedback_displayed = False
        st.session_state.current += 1
        if st.session_state.current >= len(st.session_state.questions):
            st.session_state.page = "results"
# --- PAGE 4: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    st.markdown("## ✅ Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")
    st.markdown(f"**Mode:** {st.session_state.mode} | **Category:** {st.session_state.category}")
    
    incorrect_qs = [st.session_state.questions[i] for i, a in enumerate(st.session_state.answers) if not a]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", cert, file_name="certificate.pdf", mime="application/pdf")

    append_to_json_file(LEADERBOARD_FILE, {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "timestamp": datetime.now().isoformat()
    })

    if st.checkbox("Show Leaderboard"):
        top = sorted(load_json_file(LEADERBOARD_FILE), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}")

    st.markdown("---")
    st.markdown("### 🗣️ Leave a comment (visible only to the creator):")
    comment_text = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment_text.strip():
        append_to_json_file(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment_text.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you! Your comment has been submitted.")

    st.caption("Comments are private and only visible to the game creator.")

    st.markdown("### 🔐 Admin Section")
    pw = st.text_input("Admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_json_file(COMMENTS_FILE)
        if comments:
            for c in comments:
                name = c.get('name', '???')
                comment = c.get("comment", "")
                time_str = c.get("time", "")
                st.markdown(f"**{name}** ({time_str}):")
                st.write(comment)
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json", "application/json")
        else:
            st.info("No comments yet.")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
