import streamlit as st
import json, random, time, os
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# --- File paths ---
LEADERBOARD_FILE = ".streamlit/leaderboard.json"
COMMENTS_FILE = ".streamlit/comments.json"
QUESTIONS_FILE = "questions_cleaned.json"

# --- Utility functions ---
def load_json(path):
    if not os.path.exists(path): return []
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)

def append_json(path, entry):
    data = load_json(path)
    data.append(entry)
    save_json(path, data)

def generate_certificate(name, score, total, percent):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(300, 750, "🎓 AML Quiz Certificate")
    c.setFont("Helvetica", 12)
    c.drawString(100, 700, f"Name: {name}")
    c.drawString(100, 680, f"Score: {score}/{total} ({percent}%)")
    c.drawString(100, 660, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    c.save()
    buffer.seek(0)
    return buffer

# --- App Config ---
st.set_page_config("AML Quiz", layout="centered")
if "page" not in st.session_state: st.session_state.page = "start"

# --- Page: Start ---
if st.session_state.page == "start":
    st.title("🕵️ AML Mastermind")
    st.markdown(f"Players so far: **{len(load_json(LEADERBOARD_FILE))}**")
    name = st.text_input("Enter your name to begin:")
    if st.button("Start") and name.strip():
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            qlist = json.load(f)
        random.shuffle(qlist)
        st.session_state.name = name.strip()
        st.session_state.questions = qlist[:10]
        st.session_state.current = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.session_state.page = "quiz"

# --- Page: Quiz ---
elif st.session_state.page == "quiz":
    q = st.session_state.questions[st.session_state.current]
    st.markdown(f"### Q{st.session_state.current+1}: {q['question']}")
    if f"options_{st.session_state.current}" not in st.session_state:
        opts = q["options"].copy(); random.shuffle(opts)
        st.session_state[f"options_{st.session_state.current}"] = opts
    options = st.session_state[f"options_{st.session_state.current}"]
    choice = st.radio("Choose one:", options, key=f"choice_{st.session_state.current}")
    
    if "answered" not in st.session_state or not st.session_state.answered:
        if st.button("Submit"):
            correct = q["correct_answer"].strip().lower()
            picked = choice.strip().lower()
            is_right = picked == correct
            st.session_state.answers.append(is_right)
            st.session_state.feedback = {
                "correct": q["correct_answer"],
                "explanation": q.get("explanation", "No explanation."),
                "source": q.get("source", "")
            }
            st.session_state.answered = True

    elif st.session_state.answered:
        f = st.session_state.feedback
        st.success("✅ Correct!" if st.session_state.answers[-1] else f"❌ Wrong. Correct: {f['correct']}")
        st.info(f["explanation"])
        st.caption(f"Source: {f['source']}")
        if st.button("Next"):
            st.session_state.current += 1
            st.session_state.answered = False
            if st.session_state.current >= len(st.session_state.questions):
                st.session_state.page = "results"

# --- Page: Results ---
elif st.session_state.page == "results":
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    percent = round(score / total * 100)
    duration = int(time.time() - st.session_state.start_time)
    st.success("🎉 Quiz Completed!")
    st.markdown(f"**Name:** {st.session_state.name}")
    st.markdown(f"**Score:** {score}/{total} ({percent}%)")
    st.markdown(f"**Time:** {duration} sec")
    cert = generate_certificate(st.session_state.name, score, total, percent)
    st.download_button("📄 Download Certificate", cert, "certificate.pdf")

    append_json(LEADERBOARD_FILE, {
        "name": st.session_state.name[:5] + "###",
        "score": score, "percent": percent,
        "duration": duration, "timestamp": datetime.now().isoformat()
    })

    if st.checkbox("🏆 Show Leaderboard"):
        top = sorted(load_json(LEADERBOARD_FILE), key=lambda x: (-x["score"], x["duration"]))[:10]
        for i, r in enumerate(top, 1):
            st.markdown(f"{i}. {r['name']} | {r['score']}pts | {r['duration']}s")

    st.markdown("### 💬 Leave a comment (private to creator):")
    comment = st.text_area("Your feedback:")
    if st.button("Submit Comment") and comment.strip():
        append_json(COMMENTS_FILE, {
            "name": st.session_state.name[:5] + "###",
            "comment": comment.strip(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        st.success("✅ Comment submitted!")

    st.caption("Your comment is private and not visible to other players.")

    if st.button("🔁 Play Again"):
        for k in list(st.session_state.keys()): del st.session_state[k]
