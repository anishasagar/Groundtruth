"""Checks on the plain-language text. Run from the project folder:  python tests/test_message.py

Runs every case in tests/cases.csv in replay mode (no Open-Meteo), plus a
"Not enough data" case, and checks the rules in CLAUDE.md.
"""

import datetime as dt
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import message, risk, weather  # noqa: E402

FORBIDDEN = re.compile(r"\bsafe\b|\bsafely\b|\bsafety\b|\bno risk\b|\ball clear\b|\bcaused\b", re.I)


def check_text(label, result, texts):
    for t in texts:
        assert not FORBIDDEN.search(t), f"{label}: forbidden wording in: {t}"


def check_result(label, result, place="Somewhere, Far Away Land"):
    today = dt.date.today()
    sentence = message.template_sentence(result, today)
    bullets = message.why_bullets(result)
    sms = message.sms_text(result, place)
    check_text(label, result, [sentence, sms, *bullets])

    assert "official" in sentence.lower(), f"{label}: sentence must point to official warnings"
    assert "official" in sms.lower(), f"{label}: SMS must point to official warnings"
    assert len(sms) <= 160, f"{label}: SMS is {len(sms)} characters"
    assert sms.isascii(), f"{label}: SMS should be plain ASCII"
    assert len(message.sms_text(result, "A" * 300)) <= 160, f"{label}: SMS too long with a very long place name"

    if result["level"] in risk.LEVELS:
        # The headline always matches the computed level (and no other level's headline appears).
        assert_headline(label, sentence, result["level"], today)
        assert re.search(rf"\b{result['level']}\b", sms), f"{label}: SMS level word does not match"
        # No numbers at all in the sentence (so it can't add one that isn't in the facts).
        assert not re.search(r"\d", sentence), f"{label}: sentence contains a number"
        # Action line: none for Typical, otherwise exactly one of the fixed lines.
        actions = [a for a in message.ACTIONS.values() if a in sentence]
        assert len(actions) == (0 if result["level"] == "Typical" else 1), f"{label}: action lines {actions}"
        # The "how often" lines are hidden for Typical, shown otherwise.
        assert (message.rarity_rows(result) is None) == (result["level"] == "Typical"), f"{label}: rarity rule"
        # What decided the level comes first in the Why list.
        first = bullets[0]
        assert result["level"] == "Typical" or first.startswith("**") and "Normal" not in first, f"{label}: {first}"
        assert "ERA5" not in " ".join(bullets), f"{label}: source text belongs in Details"
        assert "Level:" not in sentence and "See the reasons" not in sentence
    else:
        assert risk.NOT_ENOUGH_TEXT in sentence and risk.NOT_ENOUGH_TEXT.replace("—", "-") in sms
        assert message.rarity_rows(result) is None


def assert_headline(label, sentence, level, today):
    for other, text in message.HEADLINES.items():
        said = any(sentence.startswith(text.format(when=w)) for w in ("today", "on this day"))
        assert said == (other == level), f"{label}: headline for {other} {'missing' if other == level else 'present'}"


def not_enough_result():
    checks = [{"key": "rain_mm", "name": "Rain (24 h)", "unit": "mm", "value": None, "level": risk.NOT_ENOUGH,
               "text": risk.NOT_ENOUGH_TEXT, "notes": []}]
    checks.append({**checks[0], "key": "recent_rain_mm", "name": risk.RECENT_RAIN_NAME,
                   "before_total": None, "daily_amounts": [None] * 6, "source": "forecast"})
    return {"level": risk.NOT_ENOUGH, "date": dt.date(2025, 1, 1), "checks": checks, "decided_by": [],
            "baseline_label": risk.baseline_label(), "recent_label": "1995–2024", "notes": []}


def main():
    cases = pd.read_csv(ROOT / "tests" / "cases.csv", dtype=str)
    with weather.offline():
        for _, c in cases.iterrows():
            result = risk.assess(float(c["latitude"]), float(c["longitude"]), dt.date.fromisoformat(c["date"]))
            check_result(c["name"], result)
            if c["name"].startswith("Kolkata heat"):
                assert message.why_bullets(result)[0] == (
                    "**Feels like 41 °C** — above the 40 °C danger line. Heat like this is common here "
                    "(about 48 days a year) and 1.4 times more common than in 1951–1980."), message.why_bullets(result)[0]
            if result["level"] != "Typical":
                rows, _ = message.rarity_rows(result)
                assert [r["label"] for r in rows] == [result["baseline_label"], result["recent_label"]]
                assert max(r["width"] for r in rows) in (0.0, 1.0)
            print("ok:", c["name"], "->", result["level"])
    check_result("Not enough data", not_enough_result())
    print("ok: Not enough data")
    # Every level/hazard combination, using made-up checks.
    for level in risk.LEVELS:
        for key in ("rain_mm", "recent_rain_mm", "feels_like_max_c", "gust_max_kmh"):
            per = {"count": 3, "years": 30, "per_year": 0.1, "every_n_years": 10}
            check = {"key": key, "name": key, "unit": "mm", "value": 50.0, "level": level, "text": "t",
                     "baseline": per, "recent": per}
            r = {"level": level, "date": dt.date(2025, 1, 1), "checks": [check], "baseline_label": "1951–1980",
                 "recent_label": "1995–2024"}
            sentence = message.template_sentence(r, dt.date(2025, 1, 1))
            assert_headline("synthetic", sentence, level, dt.date(2025, 1, 1))
    print("ok: every level and hazard")
    print("All message checks passed.")


if __name__ == "__main__":
    main()
