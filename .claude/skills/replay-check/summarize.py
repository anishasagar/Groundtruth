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
    """The text written by code, the template sentence, and Claude's full saved reply, as Markdown lines."""
    special = replays.SPECIAL_NOTES.get(case["name"])
    action = message.action_line(result)
    lines = [f"#### {case['name']} — {case['date']} — {result['level']}", "",
             "Written by code (shown in both modes):", "",
             f"- What it means (shown with Claude's text): \"{message.what_it_means(result, special)}\"",
             f"- SMS: \"{message.sms_text(result, place, special)}\"", "",
             "Template mode:", "",
             f"- Sentence: \"{message.template_sentence(result)}\"",
             "- Action line: " + (f'"{action}"' if action else "none"), ""]
    path = replays.claude_reply_file(case["name"])
    if case["name"] not in replays.REPLAY_PLACES or not path.exists():
        return lines + ["Claude: no saved Claude reply — template mode only.", ""]
    facts = claude_text.facts(result, place, dt.date.today(), special)
    passed, problems = claude_text.saved_reply(path, facts)
    status = "passes the guardrail (shown in the app)" if passed else \
        f"does NOT pass, so the app shows template mode: {'; '.join(problems)}"
    reply = json.loads(path.read_text())["reply"]
    lines += [f"Claude's saved reply ({saved_tries(case)} {'try' if saved_tries(case) == '1' else 'tries'}) — "
              f"{status}:", "",
              *[f"- {k}: \"{v}\"" for k, v in reply.items() if isinstance(v, str)
                and k not in ("headline", "confidence_note")],  # an old-format reply shows its extra parts
              f"- Headline: \"{reply.get('headline')}\"",
              "- Why:", *[f"  - \"{b}\"" for b in reply.get("why", [])],
              f"- Confidence note: \"{reply.get('confidence_note')}\"", ""]
    return lines


def main():
    before = levels_in_testlog()
    subprocess.run([sys.executable, str(ROOT / "scripts" / "replay.py")], check=True, cwd=ROOT)

    cases = pd.read_csv(CASES, dtype=str, keep_default_na=False)
    rows, changes, full = [], [], []
    for _, case in cases.iterrows():
        previous = before.get(case["name"], "—")
        if not case["date"]:
            rows.append(f"| {case['name']} | — | pending | {previous} | — | — | — |")
            continue
        try:
            with weather.offline():
                result = risk.assess(float(case["latitude"]), float(case["longitude"]),
                                     dt.date.fromisoformat(case["date"]))
        except Exception as e:  # replay.py already logged why; keep the row
            rows.append(f"| {case['name']} | {case['date']} | not run | {previous} | — | — | — |")
            full += [f"#### {case['name']} — {case['date']}", "", f"Not run: {e}", ""]
            continue
        place = replays.place_of(case)
        template = message.template_sentence(result)
        shown = f"template mode: {template}"
        if case["name"] in replays.REPLAY_PLACES:
            facts = claude_text.facts(result, place, dt.date.today(), replays.SPECIAL_NOTES.get(case["name"]))
            reply, _ = claude_text.saved_reply(replays.claude_reply_file(case["name"]), facts)
            if reply:
                shown = f"Claude: {reply['headline']}"
        level = result["level"]
        rows.append(f"| {case['name']} | {case['date']} | **{level}** | {previous} | {shown} | {template} "
                    f"| {saved_tries(case)} |")
        if previous not in ("—", "pending", level):
            changes.append(f"- {case['name']}: {previous} → **{level}**")
        full += full_output(case, result, place)

    out = [
        "## Replay check: date, level and sentence",
        "",
        f"Added by the replay-check skill on {dt.date.today().isoformat()}. "
        "\"Previous level\" is the level in TESTLOG.md before this run.",
        "",
        "| Case | Date | Level | Previous level | Sentence shown | Template sentence | Claude tries |",
        "|---|---|---|---|---|---|---|",
        *rows,
        "",
        "### Level changes since the last run",
        "",
        *(changes or ["None."]),
        "",
        "### Full output per case",
        "",
        "The actual text a person would see: what code writes on every day (what it means, the text message), "
        "the template sentence (shown whenever Claude or the guardrail fails), and Claude's full saved reply "
        "(headline, why, confidence note) with how many tries it took.",
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
