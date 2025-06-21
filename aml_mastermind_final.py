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

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]
ADMIN_PASSWORD = "iloveaml2025"

# --- PERSISTENCE ---
def ensure_dirs():
    os.makedirs(".streamlit", exist_ok=True)
    for path in [LEADERBOARD_PATH, COMMENTS_PATH]:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump([], f)

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_json(path, entry):
    data = load_json(path)
    data.append(entry)
    save_json(path, data)

# --- CERTIFICATE ---
def generate_certificate(player_name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "📜 AML Serious Game Certificate")
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
        c.drawString(100, y, "⚠️ Areas to Improve (based on incorrect answers):")
        y -= 20
        for q in incorrect_qs:
            c.setFont("Helvetica", 10)
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation')}"
            ]
            for line in lines:
                wrapped = [line[i:i+90] for i in range(0, len(line), 90)]
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

# --- LOAD QUESTIONS ---
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

# --- INIT STATE ---
def init_state():
    defaults = {
        "page": "name",
        "player_name": "",
        "mode": None,
        "category": None,
        "questions": [],
        "current": 0,
        "answers": [],
        "start_time": None,
        "time_limit": None,
        "submitted": False,
        "feedback_shown": False,
        "leaderboard_saved": False,
        "comment": "",
        "admin_mode": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# --- MAIN APP ---
ensure_dirs()
init_state()
questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = len(load_json(LEADERBOARD_PATH))

st.set_page_config(page_title="AML Serious Game", layout="centered")

if st.session_state["page"] == "name":
    st.title("🕵️ AML Serious Game for Supervisors")
    st.markdown(f"👤 Total Players: **{player_count}**")
    st.session_state["player_name"] = st.text_input("Enter your name to begin:")
    if st.session_state["player_name"]:
        st.session_state["page"] = "instructions"
        st.experimental_rerun()

elif st.session_state["page"] == "instructions":
    st.title("📘 Instructions")
    st.markdown("""
Welcome to the AML Serious Game for Supervisors!  
Test your knowledge on AML/CFT across banking, crypto, and investment funds.

**🚨 Disclaimer:**  
This game is for educational purposes only. There may be simplifications. This is not legal advice.

### Game Modes:
- **Classic Quiz**: Choose how many questions
- **Time Attack**: Beat the clock!

Results include certificate, leaderboard, and feedback.

---
    """)
    if st.button("Start"):
        st.session_state["page"] = "setup"
        st.experimental_rerun()

elif st.session_state["page"] == "setup":
    st.title("🎮 Game Setup")
    st.session_state["mode"] = st.selectbox("Choose a Mode:", ["Classic Quiz", "Time Attack"])
    st.session_state["category"] = st.selectbox("Select a Category", list(grouped.keys()))

    if st.session_state["mode"] == "Classic Quiz":
        num_questions = st.slider("Number of Questions", 5, 30, 10)
    else:
        st.session_state["time_limit"] = st.selectbox("Time Limit (seconds)", TIME_OPTIONS)

    if st.button("Begin Game"):
        pool = grouped.get(st.session_state["category"], [])
        random.shuffle(pool)
        st.session_state["questions"] = pool[:num_questions] if st.session_state["mode"] == "Classic Quiz" else pool
        st.session_state["start_time"] = time.time()
        st.session_state["page"] = "quiz"
        st.experimental_rerun()

elif st.session_state["page"] == "quiz":
    if st.session_state["mode"] == "Time Attack":
        remaining = st.session_state["time_limit"] - int(time.time() - st.session_state["start_time"])
        if remaining <= 0:
            st.session_state["page"] = "results"
            st.experimental_rerun()
        st.markdown(f"⏱ Time Left: **{remaining} seconds**")

    idx = st.session_state["current"]
    question = st.session_state["questions"][idx]
    st.markdown(f"### Question {idx+1}: {question['question']}")

    if f"options_{idx}" not in st.session_state:
        options = question["options"]
        st.session_state[f"options_{idx}"] = options

    selected = st.radio("Choose your answer:", st.session_state[f"options_{idx}"], key=f"answer_{idx}")

    if not st.session_state["feedback_shown"]:
        if st.button("Submit"):
            is_correct = selected.strip().lower() == question["correct_answer"].strip().lower()
            st.session_state["answers"].append(is_correct)
            st.session_state["feedback_shown"] = True
            st.session_state[f"feedback_{idx}"] = {
                "correct": is_correct,
                "explanation": question.get("explanation", "No explanation."),
                "source": question.get("source", "Unknown"),
                "correct_answer": question["correct_answer"]
            }
            st.experimental_rerun()
    else:
        fb = st.session_state[f"feedback_{idx}"]
        st.success("✅ Correct!" if fb["correct"] else f"❌ Wrong. Correct: {fb['correct_answer']}")
        st.info(fb["explanation"])
        st.caption(f"Source: {fb['source']}")
        if st.button("Next"):
            st.session_state["current"] += 1
            st.session_state["feedback_shown"] = False
            if st.session_state["current"] >= len(st.session_state["questions"]):
                st.session_state["page"] = "results"
            st.experimental_rerun()

elif st.session_state["page"] == "results":
    total = len(st.session_state["questions"])
    score = sum(st.session_state["answers"])
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state["start_time"])

    st.title("🏁 Game Complete!")
    st.markdown(f"**Player:** {st.session_state['player_name']}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time Taken:** {duration} sec")
    st.markdown(f"**Mode:** {st.session_state['mode']} | **Category:** {st.session_state['category']}")

    if not st.session_state["leaderboard_saved"]:
        entry = {
            "name": st.session_state["player_name"][:5] + "###",
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "category": st.session_state["category"],
            "mode": st.session_state["mode"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        append_json(LEADERBOARD_PATH, entry)
        st.session_state["leaderboard_saved"] = True

    incorrect = [
        q for i, q in enumerate(st.session_state["questions"])
        if not st.session_state["answers"][i]
    ]
    cert = generate_certificate(
        st.session_state["player_name"], score, total, percent, duration, incorrect
    )
    st.download_button("📄 Download Certificate", cert, "AML_Certificate.pdf")

    st.markdown("---")
    st.markdown("## 🏆 Leaderboard")
    top = sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]
    for i, r in enumerate(top, 1):
        st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['mode']} | {r['duration']}s")

    st.markdown("---")
    st.markdown("## ✉️ Leave a Comment (visible to the creator only)")
    comment = st.text_area("Your comment:")
    if st.button("Submit Comment"):
        append_json(COMMENTS_PATH, {
            "name": st.session_state["player_name"][:5] + "###",
            "comment": comment,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Comment submitted!")

    st.markdown("---")
    st.markdown("## 🔐 Admin Login to View Comments")
    if not st.session_state["admin_mode"]:
        pw = st.text_input("Enter admin password:", type="password")
        if pw == ADMIN_PASSWORD:
            st.session_state["admin_mode"] = True
            st.experimental_rerun()
    else:
        st.markdown("### Comments")
        comments = load_json(COMMENTS_PATH)
        for c in comments:
            st.markdown(f"**{c['name']}** ({c['time']})")
            st.write(c['comment'])
