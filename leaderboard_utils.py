import json
import os
from datetime import datetime

LEADERBOARD_FILE = "leaderboard.json"

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    with open(LEADERBOARD_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_score(player_name, score, duration, correct_answers):
    leaderboard = load_leaderboard()
    entry = {
        "name": player_name[:5],  # anonymized
        "score": score,
        "correct": correct_answers,
        "duration": duration,
        "timestamp": datetime.now().isoformat()
    }
    leaderboard.append(entry)
    with open(LEADERBOARD_FILE, "w", encoding="utf-8") as f:
        json.dump(leaderboard, f, indent=2)

def get_top_players(n=10):
    leaderboard = load_leaderboard()
    # Sort by highest correct, then lowest time
    return sorted(leaderboard, key=lambda x: (-x["correct"], x["duration"]))[:n]

def get_total_players():
    leaderboard = load_leaderboard()
    return len(leaderboard)
