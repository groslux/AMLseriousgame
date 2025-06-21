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

# --- Config ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]
ADMIN_PASSWORD = "iloveaml2025"

# --- Loaders and Savers ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

def get_top_players():
    return sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x['score'], x['duration']))[:10]

# --- Certificate Generator ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🏅 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {player_name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', '')}"
            ]
            for line in lines:
                for subline in [line[i:i+100] for i in range(0, len(line), 100)]:
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

# --- Init ---
st.set_page_config(page_title="AML Mastermind", layout="centered")

@st.cache_data
def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

def group_by_category(data):
    grouped = {}
    for q in data:
        cat = q.get("category", "Other").strip()
        grouped.setdefault(cat, []).append(q)
    return grouped

def init_state():
    defaults = {
        "step": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "submitted": False,
        "selected_answer": None,
        "game_ended": False,
        "admin": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)

# --- Step: Name ---
if st.session_state.step == "name":
    st.title("🕵️ AML Mastermind")
    st.session_state.player_name = st.text_input("Enter your name to begin:")
    if st.button("Continue") and st.session_state.player_name.strip():
        st.session_state.step = "instructions"
        st.rerun()

# --- Step: Instructions ---
elif st.session_state.step == "instructions":
    st.title("📘 Instructions")
    st.markdown(f"Welcome **{st.session_state.player_name}**!")
    st.markdown("""
### 🔎 Game Instructions:
- Choose **Classic** or **Time Attack** mode.
- Select a topic: Banking, Crypto, or Investment Funds.
- Click **Submit** to see if you're right (explanation shown).
- Click **Next** to go to the next question.

### 📜 Disclaimer:
This quiz is for training purposes only. There may be simplifications and approximations. It is not legal advice.

""")
    st.session_state.mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    st.session_state.category = st.selectbox("Select Topic", list(grouped.keys()))

    if st.session_state.mode == "Classic Quiz":
        num_q = st.slider("Number of Questions", 5, 30, 10)
        st.session_state.questions = random.sample(grouped[st.session_state.category], k=num_q)
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)
        st.session_state.questions = grouped[st.session_state.category]
    if st.button("Start Game"):
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"
        st.rerun()

# --- Step: Quiz ---
elif st.session_state.step == "quiz":
    q_idx = st.session_state.current
    total_q = len(st.session_state.questions)
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.step = "results"
            st.rerun()
        st.markdown(f"⏱ Time Left: **{remaining}s**")

    question = st.session_state.questions[q_idx]
    st.markdown(f"### Question {q_idx + 1} of {total_q}")
    st.markdown(question["question"])
    if f"options_{q_idx}" not in st.session_state:
        opts = question["options"].copy()
        random.shuffle(opts)
        st.session_state[f"options_{q_idx}"] = opts
    options = st.session_state[f"options_{q_idx}"]

    picked = st.radio("Your Answer:", options, key=f"answer_{q_idx}")
    if st.button("Submit Answer") and not st.session_state.submitted:
        st.session_state.submitted = True
        st.session_state.selected_answer = picked

    if st.session_state.submitted:
        correct = question["correct_answer"].strip().lower()
        user = st.session_state.selected_answer.strip().lower()
        is_correct = correct == user
        st.success("✅ Correct!" if is_correct else f"❌ Wrong. Correct: {question['correct_answer']}")
        st.info(question.get("explanation", "No explanation provided."))
        st.caption(f"Source: {question.get('source', 'Unknown')}")
        if st.button("Next"):
            st.session_state.answers.append(is_correct)
            st.session_state.current += 1
            st.session_state.submitted = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.step = "results"
            st.rerun()

# --- Step: Results ---
elif st.session_state.step == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    incorrect_qs = [st.session_state.questions[i] for i, correct in enumerate(st.session_state.answers) if not correct]

    st.title("🏁 Quiz Complete!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Mode:** {st.session_state.mode}")
    st.markdown(f"**Topic:** {st.session_state.category}")
    st.markdown(f"**Score:** {score}/{total} → **{percent}%**")
    st.markdown(f"**Time Taken:** {duration} seconds")

    append_json(LEADERBOARD_PATH, {
        "name": st.session_state.player_name.strip()[:5] + "###",
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

    cert_buffer = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect_qs)
    st.download_button("📄 Download Your Certificate", data=cert_buffer, file_name="AML_Certificate.pdf", mime="application/pdf")

    st.markdown("### 🏆 Leaderboard (Top 10)")
    for i, r in enumerate(get_top_players(), start=1):
        st.markdown(f"{i}. {r['name']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} | {r['duration']}s")

    st.markdown("### 💬 Leave a comment for the game creator")
    st.info("Your comment is private and will not be visible to other players.")
    with st.form("comment_form"):
        comment = st.text_area("Your feedback:")
        if st.form_submit_button("Submit Comment") and comment.strip():
            append_json(COMMENTS_PATH, {
                "name": st.session_state.player_name,
                "comment": comment.strip(),
                "time": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            st.success("Thanks! Your comment has been sent.")

    st.markdown("---")
    if st.text_input("🔐 Admin Password", type="password") == ADMIN_PASSWORD:
        st.subheader("📥 All Player Comments")
        for c in load_json(COMMENTS_PATH):
            name = c.get("name", "Anonymous")
            t = c.get("time", "Unknown time")
            st.markdown(f"**{name}** ({t})")
            st.write(c.get("comment", ""))

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
