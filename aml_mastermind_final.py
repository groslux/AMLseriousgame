import streamlit as st
import json
import random
import os
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- FILE PATHS ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- UTILITIES ---
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def append_to_file(path, new_data):
    data = load_json(path)
    data.append(new_data)
    save_json(path, data)

def generate_certificate(name, score, total, percent, duration, incorrect):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(w/2, h - 80, "🎓 AML Mastermind Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, h - 120, f"Name: {name}")
    c.drawString(100, h - 140, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, h - 160, f"Duration: {duration} seconds")
    y = h - 200
    if incorrect:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(100, y, "Topics to review:")
        y -= 20
        for q in incorrect:
            c.setFont("Helvetica", 10)
            lines = [f"- {q['question']}", f"  ✔ {q['correct_answer']}", f"  ℹ {q.get('explanation', '')}"]
            for line in lines:
                c.drawString(110, y, line[:100])
                y -= 12
                if y < 60:
                    c.showPage()
                    y = h - 60
    c.save()
    buffer.seek(0)
    return buffer

# --- INIT SESSION STATE ---
if "page" not in st.session_state:
    st.session_state.page = "name"
    st.session_state.answers = []
    st.session_state.current = 0
    st.session_state.feedback_displayed = False

# --- PAGE 1: ENTER NAME ---
if st.session_state.page == "name":
    st.title("🕵️ AML Mastermind Quiz")
    count = len(load_json(LEADERBOARD_FILE))
    st.markdown(f"**Players so far:** {count}")
    name = st.text_input("Enter your name:")
    if st.button("Start"):
        if name.strip():
            st.session_state.player_name = name.strip()
            st.session_state.page = "instructions"

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.page == "instructions":
    st.subheader("📚 How it works")
    st.markdown("""
- Choose game mode and topic
- Submit answers, see feedback, and progress
- At the end, get your 🎓 certificate and 🏅 leaderboard rank  
- 🗣️ Leave private feedback to the creator

_Disclaimer: This quiz is educational and not legal advice._
    """)
    mode = st.selectbox("Select mode", ["Classic", "Time Attack"])
    all_qs = load_json(QUESTIONS_FILE)
    categories = sorted(set(q["category"] for q in all_qs))
    category = st.selectbox("Select topic", categories)

    if mode == "Classic":
        num_q = st.slider("Number of questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        time_limit = st.selectbox("Time limit (seconds)", [60, 120, 180])
        st.session_state.time_limit = time_limit
        num_q = 99

    if st.button("Begin Quiz"):
        pool = [q for q in all_qs if q["category"] == category]
        random.shuffle(pool)
        st.session_state.questions = pool[:num_q]
        st.session_state.page = "quiz"
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.start_time = time.time()
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.feedback_displayed = False

# --- PAGE 3: QUIZ ---
elif st.session_state.page == "quiz":
    idx = st.session_state.current
    q = st.session_state.questions[idx]

    if st.session_state.mode == "Time Attack":
        elapsed = int(time.time() - st.session_state.start_time)
        remaining = st.session_state.time_limit - elapsed
        st.markdown(f"⏱️ Time remaining: {remaining}s")
        if remaining <= 0:
            st.session_state.page = "results"
            st.stop()

    st.subheader(f"Question {idx+1}")
    st.write(q["question"])

    key = f"options_{idx}"
    if key not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[key] = opts

    selected = st.radio("Choose your answer:", st.session_state[key], key=f"q_{idx}")

    if not st.session_state.feedback_displayed:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = selected.strip().lower()
            is_correct = picked == correct
            st.session_state["is_correct"] = is_correct
            st.session_state["feedback_displayed"] = True
            if is_correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", ""))
            st.caption(f"Source: {q.get('source', 'Unknown')}")

    elif st.button("Next"):
        st.session_state.answers.append(st.session_state["is_correct"])
        st.session_state.current += 1
        st.session_state.feedback_displayed = False
        if st.session_state.current >= len(st.session_state.questions):
            st.session_state.page = "results"

# --- PAGE 4: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.start_time)
    st.title("✅ Quiz Completed!")
    st.markdown(f"**Name:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration}s")
    st.markdown(f"**Mode:** {st.session_state.mode} | **Topic:** {st.session_state.category}")

    wrong_qs = [st.session_state.questions[i] for i, ok in enumerate(st.session_state.answers) if not ok]
    pdf = generate_certificate(st.session_state.player_name, score, total, percent, duration, wrong_qs)
    st.download_button("📄 Download Certificate", pdf, file_name="certificate.pdf", mime="application/pdf")

    entry = {
        "name": st.session_state.player_name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "category": st.session_state.category,
        "mode": st.session_state.mode,
        "timestamp": datetime.now().isoformat()
    }
    append_to_file(LEADERBOARD_FILE, entry)

    if st.checkbox("Show Leaderboard"):
        leaders = load_json(LEADERBOARD_FILE)
        leaders.sort(key=lambda x: (-x["score"], x["duration"]))
        for i, r in enumerate(leaders[:10], 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']}")

    st.markdown("---")
    st.subheader("🗣️ Leave a comment (private)")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_to_file(COMMENTS_FILE, {
            "name": st.session_state.player_name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Thanks! Your comment was saved.")
    st.caption("⚠️ Comments are only visible to the game creator.")

    st.subheader("🔐 Admin")
    pw = st.text_input("Admin password", type="password")
    if pw == ADMIN_PASSWORD:
        comments = load_json(COMMENTS_FILE)
        for c in comments:
            st.markdown(f"**{c.get('name', '???')}** ({c.get('time', '')}):")
            st.write(c.get("comment", ""))
        st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
