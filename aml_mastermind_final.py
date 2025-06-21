import streamlit as st
import json, random, time, os, pathlib
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIG ---
LEADERBOARD_PATH = ".streamlit/leaderboard.json"
COMMENTS_PATH = ".streamlit/comments.json"
TIME_OPTIONS = [60, 120, 180]
ADMIN_PASSWORD = "iloveaml2025"

# --- FILE UTILS ---
def load_json(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    os.makedirs(pathlib.Path(path).parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- LEADERBOARD UTILS ---
def append_leaderboard(record):
    data = load_json(LEADERBOARD_PATH)
    data.append(record)
    save_json(LEADERBOARD_PATH, data)

def get_top_players():
    return sorted(load_json(LEADERBOARD_PATH), key=lambda x: (-x["score"], x["duration"]))[:10]

def get_player_count():
    return len(load_json(LEADERBOARD_PATH))

# --- CERTIFICATE ---
def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width / 2, height - 100, "🎓 AML Serious Game Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, height - 140, f"Name: {name}")
    c.drawString(100, height - 160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, height - 180, f"Duration: {duration} seconds")
    c.drawString(100, height - 200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = height - 240
    if percent >= 75:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "🎉 Excellent job! You're an AML mastermind.")
    else:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(100, y, "📌 Areas to Improve:")
        y -= 20
        for q in incorrect_qs:
            lines = [
                f"Q: {q.get('question', '')}",
                f"✔ Correct Answer: {q.get('correct_answer', '')}",
                f"ℹ Explanation: {q.get('explanation', 'No explanation')}"
            ]
            for line in lines:
                for chunk in [line[i:i+100] for i in range(0, len(line), 100)]:
                    c.drawString(110, y, chunk)
                    y -= 12
                    if y < 80: c.showPage(); y = height - 80
            y -= 10
    c.save()
    buffer.seek(0)
    return buffer

# --- SESSION SETUP ---
st.set_page_config("AML Serious Game", layout="centered")
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
defaults = {
    "step": "name",
    "player_name": "",
    "mode": None,
    "category": None,
    "questions": [],
    "current": 0,
    "answers": [],
    "submitted": False,
    "start_time": None,
    "time_limit": None,
    "game_ended": False,
    "selected_answer": "",
    "leaderboard_saved": False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

questions_data = load_questions()
grouped = group_by_category(questions_data)
player_count = get_player_count()

# --- PAGE 1: NAME ---
if st.session_state.step == "name":
    st.title("🕵️ AML Serious Game")
    st.markdown(f"<div style='text-align:center;font-size:18px;'>Players who have played: <b>{player_count}</b></div>", unsafe_allow_html=True)
    name = st.text_input("Enter your name to begin:")
    if st.button("Continue") and name.strip():
        st.session_state.player_name = name.strip()
        st.session_state.step = "instructions"
        st.experimental_rerun()

# --- PAGE 2: INSTRUCTIONS ---
elif st.session_state.step == "instructions":
    st.header("🚨 Welcome, AML Investigator!")
    st.markdown("""
**Your Mission:**  
Investigate suspicious scenarios from Banking, Crypto, and Investment Funds.

🔍 Test your AML knowledge  
🏆 Compete on the leaderboard  
📜 Earn a certificate

### 📜 Disclaimer:
This game is for training only. It may contain simplifications or mistakes. It does not constitute legal or compliance advice.

### Game Instructions:
- Choose Classic or Time Attack
- Pick a topic
- Read each question carefully
- Click **Submit Answer** to see feedback and move on
""")
    if st.button("Start Setup"):
        st.session_state.step = "setup"
        st.experimental_rerun()

# --- PAGE 3: SETUP MODE ---
elif st.session_state.step == "setup":
    st.subheader("Choose your game mode")
    mode = st.selectbox("Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Category", list(grouped.keys()))
    if mode == "Classic Quiz":
        num = st.slider("Number of questions", 5, 30, 10)
        time_limit = None
    else:
        num = None
        time_limit = st.selectbox("Time Limit (sec)", TIME_OPTIONS)

    if st.button("Start Game"):
        qlist = grouped.get(category, [])
        random.shuffle(qlist)
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.questions = qlist[:num] if num else qlist
        st.session_state.time_limit = time_limit
        st.session_state.start_time = time.time()
        st.session_state.step = "quiz"
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.game_ended = False
        st.experimental_rerun()

# --- PAGE 4: QUIZ LOOP ---
elif st.session_state.step == "quiz":
    if st.session_state.mode == "Time Attack":
        remaining = st.session_state.time_limit - int(time.time() - st.session_state.start_time)
        if remaining <= 0:
            st.session_state.step = "results"
            st.experimental_rerun()
        st.markdown(f"⏱ Time left: **{remaining} sec**")

    i = st.session_state.current
    questions = st.session_state.questions
    if i < len(questions):
        q = questions[i]
        st.markdown(f"### Question {i+1}: {q['question']}")
        if f"options_{i}" not in st.session_state:
            opts = q["options"].copy()
            random.shuffle(opts)
            st.session_state[f"options_{i}"] = opts
        selected = st.radio("Choose:", st.session_state[f"options_{i}"], key=f"answer_{i}")
        if st.button("Submit Answer"):
            correct = q["correct_answer"].strip().lower()
            st.session_state.answers.append(selected.strip().lower() == correct)
            st.success("✅ Correct!" if selected.strip().lower() == correct else f"❌ Wrong! Correct: {q['correct_answer']}")
            st.info(q.get("explanation", "No explanation."))
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
            st.session_state.current += 1
            time.sleep(1.5)
            st.experimental_rerun()
    else:
        st.session_state.step = "results"
        st.experimental_rerun()

# --- PAGE 5: RESULTS ---
elif st.session_state.step == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.questions)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)

    st.header("✅ Game Over!")
    st.markdown(f"**Player:** {st.session_state.player_name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration}s  |  **Mode:** {st.session_state.mode}  |  **Category:** {st.session_state.category}")

    if not st.session_state.leaderboard_saved:
        append_leaderboard({
            "name": st.session_state.player_name[:5] + "###",
            "score": score,
            "total": total,
            "percent": percent,
            "duration": duration,
            "mode": st.session_state.mode,
            "category": st.session_state.category,
            "timestamp": datetime.now().isoformat()
        })
        st.session_state.leaderboard_saved = True

    incorrect = [q for i, q in enumerate(st.session_state.questions) if not st.session_state.answers[i]]
    cert = generate_certificate(st.session_state.player_name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Certificate", cert, file_name="AML_Certificate.pdf", mime="application/pdf")

    if st.checkbox("🏆 Show Leaderboard"):
        for i, r in enumerate(get_top_players(), 1):
            st.markdown(f"{i}. {r['name']} | {r['score']}/{r['total']} | {r['duration']}s | {r['category']}")

    st.markdown("---")
    st.markdown("### 💬 Leave a Comment")
    comment = st.text_area("Your feedback (private):", key="comment_box")
    if st.button("Submit Comment") and comment.strip():
        comments = load_json(COMMENTS_PATH)
        comments.append({
            "player": st.session_state.player_name,
            "comment": comment.strip(),
            "timestamp": datetime.now().isoformat()
        })
        save_json(COMMENTS_PATH, comments)
        st.success("Comment saved. Thank you!")

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

# --- ADMIN COMMENTS ---
if st.sidebar.text_input("Admin password", type="password") == ADMIN_PASSWORD:
    st.sidebar.markdown("### 🛡 Admin: Comments")
    for c in load_json(COMMENTS_PATH):
        st.sidebar.write(f"{c['timestamp']} - {c['player']}: {c['comment']}")
