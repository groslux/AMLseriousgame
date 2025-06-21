import streamlit as st
import json
import os
import pathlib
from datetime import datetime

# --- CONFIG ---
COMMENTS_FILE = ".streamlit/comments.json"
ADMIN_PASSWORD = "iloveaml2025"

# --- INIT ---
st.set_page_config(page_title="AML Serious Game", layout="centered")

# --- COMMENT STORAGE ---
def load_comments():
    if not os.path.exists(COMMENTS_FILE):
        return []
    with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_comment(comment_data):
    os.makedirs(pathlib.Path(COMMENTS_FILE).parent, exist_ok=True)
    comments = load_comments()
    comments.append(comment_data)
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=2)

# --- MAIN CONTENT ---
st.title("🎯 AML Serious Game")

# Game or results go here...
st.markdown("📝 *End of game content... certificate, leaderboard, etc.*")

# --- COMMENT SECTION ---
st.markdown("---")
st.markdown("### 💬 Leave a comment")
st.markdown("*Comments are private and only visible to the game creator.*")

player_name = st.session_state.get("player_name", "")
comment = st.text_area("Your feedback", placeholder="What did you like? What can we improve?")

if st.button("Submit Comment"):
    if comment.strip():
        save_comment({
            "name": player_name.strip()[:5] + "###",
            "comment": comment.strip(),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Thank you for your feedback!")
    else:
        st.warning("Please write something before submitting.")

# --- ADMIN SECTION TO VIEW COMMENTS ---
with st.expander("🔒 Admin - View Comments"):
    pw = st.text_input("Enter admin password", type="password")
    if pw == ADMIN_PASSWORD:
        st.success("Access granted.")
        comments = load_comments()
        if comments:
            st.json(comments)
            st.download_button("📥 Download Comments", json.dumps(comments, indent=2), file_name="comments.json")
        else:
            st.info("No comments yet.")
    elif pw:
        st.error("Incorrect password.")

# --- FOOTER ---
st.markdown("---")
st.caption("© 2025 - AML Serious Game powered by Streamlit")
