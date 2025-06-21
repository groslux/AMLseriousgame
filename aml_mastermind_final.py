import streamlit as st
import json
import random
import time
import os
import pathlib
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
PASSWORD = "iloveaml2025"
TIME_OPTIONS = [60, 120, 180]

# --- UTILS ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_record(path, record):
    data = load_json(path)
    data.append(record)
    save_json(path, data)

def get_top_players():
    return sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]

def get_player_count():
    return len(load_json(LEADERBOARD_PATH))

# --- CERTIFICATE ---
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
        c.drawString(100, y, "🎉 Congratulations! You performed excellently.")
    else:
        c.drawString(100, y, "🔍 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation provided.')}"
            ]
            for line in lines:
                for i in range(0, len(line), 100):
                    c.drawString(110, y, line[i:i+100])
                    y -= 12
                    if y < 80:
                        c.showPage()
                        y = height - 80
            y -= 10
        categories = sorted(set(q.get("category", "Other") for q in incorrect_qs))
        c.drawString(100, y, "📚 Suggested Topics:")
        y -= 16
        for cat in categories:
            c.drawString(120, y, f"- {cat}")
            y -= 12
            if y < 80:
                c.showPage()
                y = height - 80
    c.save()
    buffer.seek(0)
    return buffer

# --- SESSION INIT ---
def init_state():
    st.session_state.setdefault("step", "name")
    st.session_state.setdefault("player_name", "")
    st.session_state.setdefault("mode", "")
    st.session_state.setdefault("category", "")
    st.session_state.setdefault("questions", [])
    st.session_state.setdefault("current", 0)
    st.session_state.setdefault("answers", [])
    st.session_state.setdefault("submitted", False)
    st.session_state.setdefault("start_time", None)
    st.session_state.setdefault("time_limit", None)
    st.session_state.setdefault("score_done", False)
    st.session_state.setdefault("comment", "")

# --- MAIN ---
st.set_page_config(page_title="AML Serious Game", layout="centered")
init_state()

@st.cache_data
def load_questions():
    with open("questions_cleaned.json", "r", encoding="utf-8") as f:
        return json.load(f)

questions_data = load_questions()
grouped = {}
for q in questions_data:
    grouped.setdefault(q.get("category", "Other").strip(), []).append(q)

# --- ADMIN ---
if st.sidebar.text_input("🔐 Admin Password", type="password") == PASSWORD:
    st.sidebar.markdown("### 💬 Player Comments")
    comments = load_json(COMMENTS_PATH)
    for c in comments:
        st.sidebar.markdown(f"**{c['name']}** ({c.get('time', 'n/a')}): {c['comment']}")

# --- PAGE 1: NAME ---
if st.session_state.step == "name":
    st.title("AML Serious Game 🕵️‍♂️")
    st.markdown("Players who already played: **" + str(get_player_count()) + "**")
    name = st.text_input("Enter your name to start:")
    if name:
        st.session_state.player_name = name
        st.session_state.step = "instructions"

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.step == "instructions":
    st.title("🎯 How the Game Works")
    st.markdown("""
- Choose **Classic** or **Time Attack** mode  
- Select a topic: Crypto, Banking, or Funds  
- Answer questions by selecting and clicking **Submit**  
- After feedback, click **Next** to move forward  
- You'll get a 🏆 leaderboard spot and 📜 certificate

🛡️ **Disclaimer**: For educational use only. May contain simplifications. Not legal advice.
""")
    if st.button("Start"):
        st.session_state.step = "quiz"

# --- PAGE 3: QUIZ SETUP + EXECUTION ---
elif st.session_state.step == "quiz":
    if not st.session_state.questions:
        mode = st.selectbox("Choose game mode", ["Classic Quiz", "Time Attack"])
        category = st.selectbox("Choose category", list(grouped.keys()))
        st.session_state.mode = mode
        st.session_state.category = category
        pool = grouped[category]
        random.shuffle(pool)
        if mode == "Classic Quiz":
            num = st.slider("Number of questions", 5, 30, 10)
            st.session_state.questions = pool[:num]
        else:
            time_limit = st.selectbox("Time limit (seconds)", TIME_OPTIONS)
            st.session_state.questions = pool
            st.session_state.time_limit = time_limit
        if st.button("Begin Quiz"):
            st.session_state.start_time = time.time()
    else:
        q_idx = st.session_state.current
        questions = st.session_state.questions

        if st.session_state.mode == "Time Attack":
            remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
            if remaining <= 0:
                st.session_state.step = "results"
            else:
                st.markdown(f"⏳ Time left: **{remaining} sec**")

        if q_idx < len(questions):
            q = questions[q_idx]
            options = q["options"].copy()
            random.shuffle(options)
            st.markdown(f"### Q{q_idx+1}: {q['question']}")
            picked = st.radio("Your answer:", options, key=f"q_{q_idx}")

            if not st.session_state.submitted:
                if st.button("Submit"):
                    st.session_state.submitted = True
                    correct = q["correct_answer"].strip().lower()
                    user = picked.strip().lower()
                    is_correct = user == correct
                    st.session_state.answers.append(is_correct)
                    st.success("✅ Correct!" if is_correct else f"❌ Wrong! Correct answer: {q['correct_answer']}")
                    st.info(q.get("explanation", "No explanation provided."))
                    st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
            else:
                if st.button("Next"):
                    st.session_state.current += 1
                    st.session_state.submitted = False
        else:
            st.session_state.step = "results"

# --- PAGE 4: RESULTS + CERTIFICATE + COMMENT ---
elif st.session_state.step == "results":
    if not st.session_state.score_done:
        score = sum(st.session_state.answers)
        total = len(st.session_state.questions)
        percent = round(score / total * 100)
        duration = int(time.time() - st.session_state.start_time)
        append_record(LEADERBOARD_PATH, {
            "name": st.session_state.player_name.strip()[:5] + "###",
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.session_state.score = score
        st.session_state.total = total
        st.session_state.percent = percent
        st.session_state.duration = duration
        st.session_state.score_done = True

    st.markdown("## ✅ Quiz Complete!")
    st.markdown(f"**Score**: {st.session_state.score}/{st.session_state.total} ({st.session_state.percent}%)")
    st.markdown(f"**Duration**: {st.session_state.duration} seconds")

    cert = generate_certificate(
        st.session_state.player_name,
        st.session_state.score,
        st.session_state.total,
        st.session_state.percent,
        st.session_state.duration,
        [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    )
    st.download_button("📄 Download Certificate", cert, file_name="AML_Certificate.pdf")

    st.markdown("### 🗣️ Leave a comment (only seen by the creator):")
    comment = st.text_area("Your message", key="comment")
    if st.button("Submit Comment"):
        append_record(COMMENTS_PATH, {
            "name": st.session_state.player_name.strip()[:5] + "###",
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Comment submitted!")

    st.markdown("### 🏆 Top 10 Players")
    for i, r in enumerate(get_top_players(), start=1):
        st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}")

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
