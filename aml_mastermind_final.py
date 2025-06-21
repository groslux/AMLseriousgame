# aml_mastermind_final.py
import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# --- Config ---
COMMENTS_PATH = ".streamlit/comments.json"
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
QUESTIONS_PATH = "questions_cleaned.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- Utilities ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

def get_top_players():
    leaderboard = load_json(LEADERBOARD_PATH)
    return sorted(leaderboard, key=lambda x: (-x['score'], x['duration']))[:10]

def generate_certificate(player, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height-80, "🏅 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height-120, f"Name: {player}")
    c.drawString(100, height-140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height-160, f"Duration: {duration} sec")
    c.drawString(100, height-180, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height-220
    if percent >= 75:
        c.drawString(100, y, "✅ Great job! You're an AML pro.")
    else:
        c.drawString(100, y, "⚠️ Areas to improve:")
        y -= 20
        for q in incorrect_qs:
            for line in [
                f"Q: {q['question']}",
                f"✔ Correct: {q['correct_answer']}",
                f"ℹ {q.get('explanation','No explanation.')}"
            ]:
                for chunk in [line[i:i+95] for i in range(0, len(line), 95)]:
                    c.drawString(110, y, chunk)
                    y -= 12
                    if y < 100:
                        c.showPage()
                        y = height-80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- Session Setup ---
st.set_page_config(page_title="AML Mastermind", layout="centered")
if "step" not in st.session_state: st.session_state.step = "name"
if "player_name" not in st.session_state: st.session_state.player_name = ""
if "mode" not in st.session_state: st.session_state.mode = None
if "category" not in st.session_state: st.session_state.category = None
if "questions" not in st.session_state: st.session_state.questions = []
if "current_q" not in st.session_state: st.session_state.current_q = 0
if "score" not in st.session_state: st.session_state.score = 0
if "answers" not in st.session_state: st.session_state.answers = []
if "start_time" not in st.session_state: st.session_state.start_time = None
if "submitted" not in st.session_state: st.session_state.submitted = False
if "selected" not in st.session_state: st.session_state.selected = None
if "authenticated" not in st.session_state: st.session_state.authenticated = False

# --- Load Questions ---
@st.cache_data
def load_questions():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

questions_all = load_questions()
categories = sorted(set(q.get("category", "Other") for q in questions_all))

# --- Page: Name ---
if st.session_state.step == "name":
    st.title("🔐 AML Mastermind Deluxe")
    st.markdown("Enter your name to start:")
    name = st.text_input("Name:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.step = "instructions"
        st.rerun()

# --- Page: Instructions ---
elif st.session_state.step == "instructions":
    st.title("🕵️ AML Serious Game")
    st.markdown("""
Welcome to the AML Serious Game for Supervisors!  
**🧠 Test your knowledge – 🏆 Beat the leaderboard – 📄 Earn your certificate**

### 🧪 How it works:
- Select your game mode and category
- Answer each question
- After feedback, click **Next** to continue
- Get feedback, a certificate, and leaderboard rank at the end

📝 **Disclaimer**: This game is for training only. It may include simplifications or errors. It is not legal advice.
""")
    st.selectbox("Select game mode:", ["Classic Quiz"], key="mode")
    st.selectbox("Select topic:", categories, key="category")
    st.slider("Number of questions:", 5, 20, 10, key="num_q")
    if st.button("Start Game"):
        q_pool = [q for q in questions_all if q["category"] == st.session_state.category]
        random.shuffle(q_pool)
        st.session_state.questions = q_pool[:st.session_state.num_q]
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"
        st.rerun()

# --- Page: Quiz ---
elif st.session_state.step == "quiz":
    current = st.session_state.current_q
    questions = st.session_state.questions
    total = len(questions)
    if current >= total:
        st.session_state.step = "results"
        st.rerun()
    question = questions[current]
    st.markdown(f"**Question {current+1} of {total}:** {question['question']}")
    if f"shuffled_{current}" not in st.session_state:
        shuffled = question["options"][:]
        random.shuffle(shuffled)
        st.session_state[f"shuffled_{current}"] = shuffled
    options = st.session_state[f"shuffled_{current}"]
    st.radio("Options:", options, key="selected")
    if not st.session_state.submitted:
        if st.button("Submit"):
            st.session_state.submitted = True
            st.session_state.selected = st.session_state.selected
            correct = question["correct_answer"]
            is_correct = st.session_state.selected.strip().lower() == correct.strip().lower()
            st.session_state.answers.append(is_correct)
            if is_correct: st.session_state.score += 1
            st.success("✅ Correct!" if is_correct else f"❌ Incorrect. Correct answer: {correct}")
            st.info(question.get("explanation", "No explanation provided."))
            st.caption(f"Source: {question.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.submitted = False
            st.session_state.selected = None
            st.session_state.current_q += 1
            st.rerun()

# --- Page: Results ---
elif st.session_state.step == "results":
    total = len(st.session_state.questions)
    score = st.session_state.score
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.title("✅ Quiz Complete!")
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Duration:** {duration} seconds")

    incorrect_qs = [
        st.session_state.questions[i]
        for i, is_correct in enumerate(st.session_state.answers) if not is_correct
    ]

    # Leaderboard
    player_record = {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "category": st.session_state.category,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    append_json(LEADERBOARD_PATH, player_record)

    st.markdown("### 🏆 Leaderboard")
    for i, r in enumerate(get_top_players(), start=1):
        st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s")

    # Certificate
    cert = generate_certificate(
        st.session_state.player_name, score, total, percent, duration, incorrect_qs
    )
    st.download_button("📄 Download Your Certificate", cert, "certificate.pdf")

    # Comments
    st.markdown("### 💬 Leave a comment (only visible to the game creator)")
    comment = st.text_area("Your comment:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_PATH, {
            "name": st.session_state.player_name,
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thanks for your feedback!")

    if st.checkbox("🔐 Admin Login"):
        pw = st.text_input("Password", type="password")
        if pw == ADMIN_PASSWORD:
            comments = load_json(COMMENTS_PATH)
            st.markdown("### All Player Comments")
            for c in comments:
                st.markdown(f"**{c['name']}** ({c['time']}):")
                st.write(c["comment"])
            st.download_button("⬇ Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
