import streamlit as st
import json
import random
import time
import uuid
from datetime import datetime
import os

# --- Page Setup ---
st.set_page_config(page_title="AML Mastermind Deluxe", layout="centered")
st.title("🧠 AML Mastermind Deluxe")

# --- Constants ---
PASSWORD = "iloveaml2025"
QUESTIONS_FILE = "questions_cleaned.json"
LEADERBOARD_FILE = "leaderboard.json"

# --- Load questions ---
@st.cache_data
def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def group_questions(data):
    grouped = {}
    for q in data:
        category = q.get("category", "Other").strip()
        grouped.setdefault(category, []).append(q)
    return grouped

# --- Load leaderboard ---
def load_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_leaderboard(data):
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --- Authenticate ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 AML Mastermind Deluxe")
    pw = st.text_input("Enter the password:", type="password")
    if pw == PASSWORD:
        st.session_state.authenticated = True
    else:
        st.stop()



# --- Player name and Game Setup ---
if "game_ready" not in st.session_state:
    st.session_state.game_ready = False

if not st.session_state.game_ready:
    st.title("🕵️ AML Mastermind Deluxe")
    st.subheader("Enter your details to begin")

    name = st.text_input("Your name")
    mode = st.selectbox("Choose Game Mode", ["Classic Quiz", "Time Attack"])
    category = st.selectbox("Choose a Category", ["Crypto", "Banking", "Collective Investment Sector"])
    start_button = st.button("Start Game")

    if start_button and name.strip():
        st.session_state.name = name.strip()
        st.session_state.mode = mode
        st.session_state.category = category
        st.session_state.game_ready = True
        st.session_state.current = 0
        st.session_state.score = 0
        st.session_state.answers = []
        st.session_state.start_time = time.time()
        st.experimental_rerun()  # Required to render next screen
    elif start_button and not name.strip():
        st.warning("Please enter your name before starting.")
    st.stop()


# --- Game Loop ---
if st.session_state.questions and not st.session_state.game_over:
    i = st.session_state.current
    if i < len(st.session_state.questions):
        q = st.session_state.questions[i]

        if st.session_state.mode == "Time Attack":
            remaining = st.session_state.duration - int(time.time() - st.session_state.start_time)
            if remaining <= 0:
                st.session_state.game_over = True
                st.rerun()
            st.markdown(f"⏳ Time left: **{remaining}s**")

        st.subheader(f"Q{i+1}: {q['question']}")
        options = q["options"].copy()
        random.shuffle(options)
        selected = st.radio("Your answer:", options, key=f"q_{i}")
        if st.button("Submit", key=f"submit_{i}"):
            correct = selected.strip().lower() == q["correct_answer"].strip().lower()
            st.session_state.answers.append(correct)
            if correct:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ Incorrect. The correct answer was: {q['correct_answer']}")
            st.info(f"💡 {q.get('explanation', 'No explanation provided.')}")
            st.caption(f"📚 Source: {q.get('source', 'Unknown')}")
            st.session_state.current += 1
            if st.session_state.mode == "Time Attack":
                time.sleep(1)  # Small pause before next question
            st.rerun()

    else:
        st.session_state.game_over = True
        st.rerun()

# --- Game Over Screen ---
if st.session_state.game_over:
    score = sum(st.session_state.answers)
    total = len(st.session_state.answers)
    duration = int(time.time() - st.session_state.start_time) if st.session_state.start_time else 0
    pct = int(score / total * 100) if total else 0

    st.markdown("## 🏁 Quiz Complete!")
    st.markdown(f"### 🧮 Score: {score}/{total} ({pct}%)")
    st.markdown(f"⏱️ Duration: {duration} seconds")
    if pct >= 75:
        st.success("🏆 You earned a certificate!")
    else:
        st.info("Try again to reach 75% and earn a certificate.")

    # --- Save to leaderboard ---
    new_record = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": f"Player_{str(uuid.uuid4())[:4]}",
        "score": score,
        "total": total,
        "mode": st.session_state.mode,
        "category": st.session_state.category,
        "duration": duration
    }
    leaderboard = load_leaderboard()
    leaderboard.append(new_record)
    save_leaderboard(leaderboard)

    # --- Replay ---
    if st.button("🔁 Play Again"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

# --- Leaderboard ---
with st.expander("📊 Show Leaderboard"):
    lb = load_leaderboard()
    lb_sorted = sorted(lb, key=lambda x: (x["score"], -x["duration"]), reverse=True)
    for r in lb_sorted[:10]:
        pct = int(r['score'] / r['total'] * 100) if r['total'] else 0
        st.markdown(f"- {r['timestamp']} | {r['mode']} | {r['category']} | {r['score']}/{r['total']} ({pct}%) in {r['duration']}s")

# --- Footer ---
st.markdown("---")
st.caption("© 2025 – AML Mastermind | Powered by FATF • IOSCO • IMF • World Bank")
