"""Run scripts/replay.py, then add to TESTLOG.md the date, level and sentence for each case,
the level changes since the last run, and the full text a person would see for each case.

Run from the project folder:  python .claude/skills/replay-check/summarize.py

replay.py rewrites TESTLOG.md from scratch, so this reads the previous levels first.
Never calls Open-Meteo or Claude: it only uses the saved data and saved Claude replies.
"""

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from groundtruth import claude_text, message, replays, risk, weather  # noqa: E402

TESTLOG = ROOT / "TESTLOG.md"
CASES = ROOT / "tests" / "cases.csv"


def levels_in_testlog():
    """{case name: level} from the main table of TESTLOG.md (empty if there is no log yet)."""
    if not TESTLOG.exists():
        return {}
    levels = {}
    for line in TESTLOG.read_text().split("## ")[0].splitlines():  # the main table comes before any "## "
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) > 3 and cells[0] not in ("Case", "") and not cells[0].startswith("---"):
            levels[cells[0]] = cells[2].strip("*")
    return levels


def saved_tries(case):
    """How many times Claude was asked before its saved reply passed ("—" if not recorded)."""
    path = replays.claude_reply_file(case["name"])
    if case["name"] not in replays.REPLAY_PLACES or not path.exists():
        return "—"
    tries = json.loads(path.read_text()).get("tries")
    return "—" if tries is None else str(tries)


def full_output(case, result, place):
    """The page text (all written by code), in screen order, and Claude's saved reply (kept for Phase 2, not shown)."""
    special = replays.SPECIAL_NOTES.get(case["name"])
    blocks = message.then_and_now(result)
    title = message.headline(result)
    lines = [f"#### {case['name']} — {case['date']} — {result['level']}", "",
             "On the page (every word written by code):", "",
             f"- Level box: \"{place} · {message.day_text(result['date'])}\" / **{result['level']}** / "
             f"\"{message.level_line(result)}\"",
             f"- Headline: \"{title}\"" if title else "- Headline: none (Typical days have none)",
             *[f"- Line under the headline: \"{line}\"" for line in message.summary_lines(result, special)],
             *([f"- Then and now: \"{message.THEN_AND_NOW_CAPTION}\""] if blocks else ["- Then and now: not shown"]),
             *[f"  - {b['title']} — " + "; ".join(f"{r['label']}: {r['words']}" for r in b["rows"])
               + (f" — \"{b['rarer_now']}\"" if b["rarer_now"] else "") for b in blocks],
             "- The numbers (collapsed):", *[f"  - \"{line}\"" for line in message.number_lines(result)], "",
             f"Text message (not shown on the page; kept for Phase 2): \"{message.sms_text(result, place, special)}\"",
             ""]
    path = replays.claude_reply_file(case["name"])
    if result["level"] == "Typical" or case["name"] not in replays.REPLAY_PLACES or not path.exists():
        return lines
    facts = claude_text.facts(result, place, dt.date.today(), special)
    passed, problems = claude_text.saved_reply(path, facts)
    reply = json.loads(path.read_text())["reply"]
    status = "passes the guardrail" if passed else f"does NOT pass the guardrail: {'; '.join(problems)}"
    return lines + [f"Claude's saved headline (kept for Phase 2, not shown on the page; {saved_tries(case)} "
                    f"{'try' if saved_tries(case) == '1' else 'tries'}; {status}): \"{reply.get('headline')}\"", ""]


def main():
    before = levels_in_testlog()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "replay.py")], check=True, cwd=ROOT)

    cases = pd.read_csv(CASES, dtype=str, keep_default_na=False)
    rows, changes, full = [], [], []
    for _, case in cases.iterrows():
        previous = before.get(case["name"], "—")
        if not case["date"]:
            rows.append(f"| {case['name']} | — | pending | {previous} | — | — |")
            continue
        try:
            with weather.offline():
                result = risk.assess(float(case["latitude"]), float(case["longitude"]),
                                     dt.date.fromisoformat(case["date"]))
        except Exception as e:  # replay.py already logged why; keep the row
            rows.append(f"| {case['name']} | {case['date']} | not run | {previous} | — | — |")
            full += [f"#### {case['name']} — {case['date']}", "", f"Not run: {e}", ""]
            continue
        place = replays.place_of(case)
        shown = message.headline(result) or f"(no headline) {result['level']} {message.level_line(result)}"
        level = result["level"]
        rows.append(f"| {case['name']} | {case['date']} | **{level}** | {previous} | {shown} "
                    f"| {message.not_checked(result, replays.SPECIAL_NOTES.get(case['name']))} |")
        if previous not in ("—", "pending", level):
            changes.append(f"- {case['name']}: {previous} → **{level}**")
        full += full_output(case, result, place)

    out = [
        "## Replay check: date, level and sentence",
        "",
        f"Added by the replay-check skill on {dt.date.today().isoformat()}. "
        "\"Previous level\" is the level in TESTLOG.md before this run.",
        "",
        "| Case | Date | Level | Previous level | Headline shown (code) | Not checked box |",
        "|---|---|---|---|---|---|",
        *rows,
        "",
        "### Level changes since the last run",
        "",
        *(changes or ["None."]),
        "",
        "### Full output per case",
        "",
        "The actual text a person would see, in screen order. Every word on the page is written by code; Claude is "
        "switched off (kept for Phase 2), and its saved headline is listed only for reference.",
        "",
        *full,
    ]
    text = TESTLOG.read_text()
    footer = "Weather data by Open-Meteo.com"
    body = text.rstrip().removesuffix(footer).rstrip()
    TESTLOG.write_text(body + "\n\n" + "\n".join(out) + "\n" + footer + "\n")

    print("\nLevel changes since the last run:")
    print("\n".join(changes) if changes else "None.")
    print(f"Wrote {TESTLOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
