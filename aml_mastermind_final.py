import streamlit as st
import json
import random
import time
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# --- Paths & Config ---
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- Helpers ---
def load_data(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_data(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

def append_data(path, entry):
    data = load_data(path)
    data.append(entry)
    save_data(path, data)

def generate_certificate(name, score, total, percent, duration, incorrect_qs):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(w/2, h-100, "🎓 AML Quiz Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, h-140, f"Name: {name}")
    c.drawString(100, h-160, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, h-180, f"Duration: {duration}s")
    c.drawString(100, h-200, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    y = h-240
    if percent < 75:
        c.drawString(100, y, "Topics to Review:")
        y -= 20
        seen = set()
        for q in incorrect_qs:
            cat = q.get("category", "Other")
            if cat not in seen:
                c.drawString(120, y, f"- {cat}")
                seen.add(cat)
                y -= 15
    c.save()
    buf.seek(0)
    return buf

# --- Streamlit Config ---
st.set_page_config("AML Quiz", layout="centered")
if "page" not in st.session_state:
    st.session_state.page = "start"

# --- PAGE: START ---
if st.session_state.page == "start":
    st.title("🕵️ AML Mastermind")
    count = len(load_data(LEADERBOARD_FILE))
    st.markdown(f"Players so far: **{count}**")
    name = st.text_input("Enter your name:")
    if st.button("Continue") and name.strip():
        st.session_state.name = name.strip()
        st.session_state.page = "intro"

# --- PAGE: INTRO ---
elif st.session_state.page == "intro":
    st.header("📚 How It Works")
    st.markdown("""
- Choose Classic or Time Attack  
- Pick a topic: Crypto, Banking, Investment Funds  
- Answer each question and see feedback  
- Submit once → See if you're correct → Next  
- At the end: certificate, leaderboard, comment box

### Disclaimer:
This quiz is for training only. There may be simplifications. This is not legal advice.
    """)
    st.session_state.mode = st.selectbox("Game mode", ["Classic", "Time Attack"])
    all_qs = load_data(QUESTIONS_FILE)
    st.session_state.category = st.selectbox("Topic", sorted(set(q["category"] for q in all_qs)))
    if st.session_state.mode == "Classic":
        st.session_state.qn_count = st.slider("Number of Questions", 5, 20, 10)
        st.session_state.time_limit = None
    else:
        st.session_state.time_limit = st.selectbox("Time Limit (seconds)", [60, 120, 180])
        st.session_state.qn_count = 100  # large cap
    if st.button("Start Quiz"):
        pool = [q for q in all_qs if q["category"] == st.session_state.category]
        random.shuffle(pool)
        st.session_state.questions = pool[:st.session_state.qn_count]
        st.session_state.answers = []
        st.session_state.current = 0
        st.session_state.feedback_shown = False
        st.session_state.started = time.time()
        st.session_state.page = "quiz"

# --- PAGE: QUIZ ---
elif st.session_state.page == "quiz":
    qn = st.session_state.current
    if qn >= len(st.session_state.questions):
        st.session_state.page = "results"
        st.experimental_rerun()

    q = st.session_state.questions[qn]
    st.subheader(f"Question {qn+1}")
    st.markdown(q["question"])
    if f"opts_{qn}" not in st.session_state:
        opts = q["options"].copy()
        random.shuffle(opts)
        st.session_state[f"opts_{qn}"] = opts
    selected = st.radio("Options:", st.session_state[f"opts_{qn}"], key=f"radio_{qn}")

    if not st.session_state.feedback_shown:
        if st.button("Submit"):
            is_correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state["last_correct"] = is_correct
            st.session_state["last_selected"] = selected
            st.session_state.feedback_shown = True
            st.success("✅ Correct!") if is_correct else st.error(f"❌ Correct answer: {q['correct_answer']}")
            st.info(q.get("explanation", ""))
            st.caption(f"Source: {q.get('source', 'Unknown')}")
    else:
        if st.button("Next"):
            st.session_state.answers.append(st.session_state["last_correct"])
            st.session_state.current += 1
            st.session_state.feedback_shown = False

# --- PAGE: RESULTS ---
elif st.session_state.page == "results":
    total = len(st.session_state.answers)
    score = sum(st.session_state.answers)
    percent = round(score / total * 100) if total else 0
    duration = int(time.time() - st.session_state.started)
    st.header("✅ Quiz Completed!")
    st.markdown(f"**Player:** {st.session_state.name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration}s")
    st.markdown(f"**Mode:** {st.session_state.mode} | **Topic:** {st.session_state.category}")

    incorrect = [st.session_state.questions[i] for i, c in enumerate(st.session_state.answers) if not c]
    cert = generate_certificate(st.session_state.name, score, total, percent, duration, incorrect)
    st.download_button("📄 Download Certificate", cert, "certificate.pdf", "application/pdf")

    append_data(LEADERBOARD_FILE, {
        "name": st.session_state.name[:5] + "###",
        "score": score,
        "total": total,
        "percent": percent,
        "duration": duration,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "timestamp": datetime.now().isoformat()
    })

    if st.checkbox("Show Leaderboard"):
        top = sorted(load_data(LEADERBOARD_FILE), key=lambda x: (-x['score'], x['duration']))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. **{r['name']}** | {r['score']}/{r['total']} | {r['duration']}s | {r['mode']} | {r['category']}")

    st.markdown("---")
    st.subheader("🗣️ Leave a Comment")
    comment = st.text_area("Private comment to the game creator:")
    if st.button("Submit Comment") and comment.strip():
        append_data(COMMENTS_FILE, {
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("Comment submitted!")

    st.caption("Comments are only visible to the creator.")

    st.markdown("### 🔐 Admin Access")
    pw = st.text_input("Password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted")
        comments = load_data(COMMENTS_FILE)
        if comments:
            for c in comments:
                st.markdown(f"**{c.get('name')}** ({c.get('time')}):")
                st.write(c.get("comment", ""))
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), "comments.json")

    if st.button("Play Again"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.session_state.page = "start"
        st.experimental_rerun()
