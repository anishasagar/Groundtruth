"""Run every test case in tests/cases.csv and write the results to TESTLOG.md.

Run from the project folder:  python scripts/replay.py

Never calls Open-Meteo: it only uses the saved data in data/history/ and
data/forecasts/. To download that data, run scripts/save_replay_data.py first.
"""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import claude_text, replays, risk  # noqa: E402
from groundtruth import weather  # noqa: E402
from groundtruth.weather import LimitReached, NotAvailable  # noqa: E402

CASES = ROOT / "tests" / "cases.csv"
TESTLOG = ROOT / "TESTLOG.md"
ORDER = risk.LEVELS
COLUMNS = [name for name, _ in risk.CHECKS.values()] + [risk.RECENT_RAIN_NAME]  # the engine's check order


def _fmt(value, unit):
    return "missing" if value is None or pd.isna(value) else f"{value:.1f} {unit}"


def _match(level, lowest, highest):
    if level not in ORDER:
        return "no — not enough data"
    i = ORDER.index(level)
    if i < ORDER.index(lowest):
        return "**no — lower than expected**"
    if i > ORDER.index(highest):
        return "no — higher than expected"
    return "yes"


def _cell(check):
    """One check for the main table: what the app shows, then the check's level."""
    return f"{check['text']} → {check['level']}"


def _detail(case, result):
    lines = [f"### {case['name']} — {case['date']}", ""]
    lines.append(f"- Level: **{result['level']}** (decided by: {', '.join(result['decided_by']) or '—'})")
    lines.append(f"- Forecast: {result['forecast_source']}, grid point "
                 f"{result['forecast_grid_point']['latitude']:.2f}, {result['forecast_grid_point']['longitude']:.2f}")
    lines.append(f"- History: {result['history_source']}, grid point "
                 f"{result['history_grid_point']['latitude']:.2f}, {result['history_grid_point']['longitude']:.2f}")
    lines.append("")
    lines.append(f"| Check | Value | In {result['recent_label']} ({result['recent_phrase']}) "
                 f"| In {result['baseline_label']} | Compared with {result['baseline_label']} "
                 "| Rarity level | Danger line | Check level |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in result["checks"]:
        if c["level"] == risk.NOT_ENOUGH:
            lines.append(f"| {c['name']} | {_fmt(c['value'], c['unit'])} | — | — | — | — | — | {risk.NOT_ENOUGH} |")
            continue
        line = "—" if c["danger_line"] is None else (
            f"{c['danger_line']} {c['unit']}: {'crossed' if c['crosses_danger_line'] else 'not crossed'}")
        lines.append(
            f"| {c['name']} | {_fmt(c['value'], c['unit'])} "
            f"| {c['recent_text']} ({c['recent']['count']} {'spells' if c['name'] == risk.RECENT_RAIN_NAME else 'days'}) "
            f"| {c['baseline_text']} ({c['baseline']['count']}) | {c['ratio_text']} "
            f"| {c['relative_level']} | {line} | {c['level']} |"
        )
    rain = result["checks"][-1]
    lines.append("")
    lines.append(f"- Rain in the {risk.RECENT_RAIN_DAYS_BEFORE} days before the date: "
                 f"{_fmt(rain['before_total'], 'mm')} (from {rain['source']}); "
                 f"daily amounts: {', '.join(_fmt(a, 'mm') for a in rain['daily_amounts'])}")
    for c in result["checks"]:
        lines.append(f"- Shown for {c['name']}: \"{c['text']}\"")
    for c in result["checks"]:
        for note in c["notes"]:
            lines.append(f"- {c['name']}: {note}")
    for note in result["notes"][: len(result["notes"]) - len(risk.ALWAYS_NOTES)]:
        lines.append(f"- {note}")
    lines.append("")
    return lines


def _claude_row(case, result):
    """Whether this replay shows Claude's saved text, checked again by the guardrail (never calls Claude)."""
    if case["name"] not in replays.REPLAY_PLACES:
        return None
    facts = claude_text.facts(result, replays.place_of(case), dt.date.today(),
                              replays.SPECIAL_NOTES.get(case["name"]))
    reply, problems = claude_text.saved_reply(replays.claude_reply_file(case["name"]), facts)
    if reply is None:
        return f"| {case['name']} | {result['level']} | template mode: {claude_text.short_reason(problems)} | — |"
    return (f"| {case['name']} | {result['level']} | Claude mode: passes the checks "
            f"(fingerprint {claude_text.fingerprint(facts)[:12]}) | {reply['headline']} |")


def main():
    cases = pd.read_csv(CASES, dtype=str, keep_default_na=False)
    summary, details, claude_rows = [], [], []
    for _, case in cases.iterrows():
        if not case["date"]:  # a test day not picked yet (see scripts/save_replay_data.py)
            print(f"{case['name']}: pending, no date yet")
            summary.append(f"| {case['name']} | — | pending | — |" + " — |" * len(COLUMNS)
                           + f" {case['expect']} | — |")
            continue
        date = dt.date.fromisoformat(case["date"])
        print(f"{case['name']} ({case['date']}) ...", flush=True)
        try:
            with weather.offline():
                result = risk.assess(float(case["latitude"]), float(case["longitude"]), date)
        except (LimitReached, NotAvailable, requests.RequestException) as e:
            print(f"  could not run: {e}")
            summary.append(f"| {case['name']} | {case['date']} | not run | — |"
                           + " — |" * len(COLUMNS) + f" {case['expect']} | — |")
            details += [f"### {case['name']} — {case['date']}", "", f"Not run: {e}", ""]
            continue
        print(f"  {result['level']} (decided by: {', '.join(result['decided_by']) or '—'})")
        cells = " | ".join(_cell(c) for c in result["checks"])
        summary.append(
            f"| {case['name']} | {case['date']} | **{result['level']}** | {', '.join(result['decided_by']) or '—'} "
            f"| {cells} "
            f"| {case['expect']} | {_match(result['level'], case['lowest_expected'], case['highest_expected'])} |"
        )
        details += _detail(case, result)
        row = _claude_row(case, result)
        if row:
            claude_rows.append(row)

    not_run = sum("| not run |" in row for row in summary)
    pending = sum("| pending |" in row for row in summary)
    out = [
        "# Test log",
        "",
        f"Last run: {dt.date.today().isoformat()} with `python scripts/replay.py`.",
        *([f"**{not_run} of {len(summary)} cases could not run — see Details. Run the replay again later.**"]
          if not_run else []),
        *([f"{pending} case(s) pending: their test day hasn't been picked yet."] if pending else []),
        f"Settings: comparison period {risk.baseline_label()}; the level uses {risk.recent_phrase()}; "
        f"recent rain = {risk.RECENT_RAIN_DAYS_BEFORE} days before + the date.",
        "",
        "Each check cell shows the wording the app shows, then that check's level. "
        "Typical checks show plain wording; the full numbers for every check are in Details.",
        "",
        "| Case | Date | Level | Decided by | " + " | ".join(COLUMNS) + " | Expected | Matches? |",
        "|---|---|---|---|" + "---|" * len(COLUMNS) + "---|---|",
        *summary,
        "",
        "## Claude text (saved replies)",
        "",
        f"Each replay shows Claude's saved text ({claude_text.MODEL}) only if its fingerprint still matches the facts, "
        "prompt and model, and it passes the guardrail check again. Otherwise the app shows the template sentence. "
        "Refill with `python scripts/save_claude_replies.py`.",
        "",
        "| Replay | Level | Text shown | Claude's headline |",
        "|---|---|---|---|",
        *claude_rows,
        "",
        "## Details",
        "",
        *details,
        "Weather data by Open-Meteo.com",
        "",
    ]
    TESTLOG.write_text("\n".join(out))
    print(f"\nWrote {TESTLOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
