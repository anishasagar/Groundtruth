"""The past events offered as replays, shared by the app and the scripts.

The place names are part of the facts sent to Claude (and of each saved reply's
fingerprint), so the app and scripts/save_claude_replies.py must use the same ones.
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = ROOT / "tests" / "cases.csv"
CLAUDE_REPLIES_DIR = ROOT / "data" / "claude_replies"

# Test cases that are not offered as replays.
HIDDEN_REPLAY_PREFIX = "Ordinary"

REPLAY_PLACES = {
    "Valencia flash flood": "Paiporta, Valencia, Spain",
    "Texas Hill Country flood": "Texas Hill Country, USA",
    "Kolkata heat (KK concert)": "Kolkata, India",
    "Bayesian sinking": "Porticello, Sicily, Italy",
    "Nepal-Tibet glacier-collapse flood": "Nepal–Tibet border area",
    "Calm control 1, Paiporta": "Paiporta, Valencia, Spain",
    "Calm control 2, Kolkata": "Kolkata, India",
    "Paris snow and cold": "Paris, France",
}


# Replays where one of the app's notes matters most: what weather data missed on that day.
# The page shows the matching note: the geological sentence in the "Not checked" box (message.not_checked).
SPECIAL_NOTES = {
    "Bayesian sinking": "storm",  # a sudden local storm, too small for this data
    "Nepal-Tibet glacier-collapse flood": "geological",  # a glacier collapse, invisible to weather data
}


def load_replays():
    """The cases.csv rows offered as replays (not the hidden ones, and only those with a date)."""
    cases = pd.read_csv(CASES_FILE, dtype=str, keep_default_na=False)
    cases = cases[~cases["name"].str.startswith(HIDDEN_REPLAY_PREFIX) & (cases["date"] != "")]
    return cases.to_dict("records")


def place_of(case):
    return REPLAY_PLACES.get(case["name"], f"{float(case['latitude']):.2f}, {float(case['longitude']):.2f}")


def claude_reply_file(name):
    """data/claude_replies/<name>.json, e.g. "Calm control 1, Paiporta" -> calm-control-1-paiporta.json"""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return CLAUDE_REPLIES_DIR / f"{slug}.json"
