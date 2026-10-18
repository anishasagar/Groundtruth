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
        # The level word in the sentence always matches the computed level.
        found = re.findall(r"Level: (\w+)", sentence)
        assert found == [result["level"]], f"{label}: sentence says {found}, level is {result['level']}"
        other = [lv for lv in risk.LEVELS if lv != result["level"] and re.search(rf"\b{lv}\b", sentence)]
        assert not other, f"{label}: sentence also mentions {other}"
        assert re.search(rf"\b{result['level']}\b", sms), f"{label}: SMS level word does not match"
        # No numbers at all in the sentence (so it can't add one that isn't in the facts).
        assert not re.search(r"\d", sentence), f"{label}: sentence contains a number"
        # Action line: none for Typical, otherwise exactly one of the fixed lines.
        actions = [a for a in message.ACTIONS.values() if a in sentence]
        assert len(actions) == (0 if result["level"] == "Typical" else 1), f"{label}: action lines {actions}"
        # Chart hidden for Typical, shown otherwise.
        assert (message.chart_frame(result) is None) == (result["level"] == "Typical"), f"{label}: chart rule"
    else:
        assert risk.NOT_ENOUGH_TEXT in sentence and risk.NOT_ENOUGH_TEXT.replace("—", "-") in sms
        assert message.chart_frame(result) is None


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
            assert re.findall(r"Level: (\w+)", sentence) == [level]
    print("ok: every level and hazard")
    print("All message checks passed.")


if __name__ == "__main__":
    main()
