"""Ask Claude for each replay's text once and save it in data/claude_replies/.

Run from the project folder:  python scripts/save_claude_replies.py
Add --refresh to ask again even when the saved reply is still up to date.

Typical days use fixed wording and never go to Claude, so Typical replays have no
saved reply (an old one is deleted). Replays in the app only use these saved replies, so the demo works without the
Claude API. Each saved reply carries a fingerprint of the facts, the prompt and
the model; if any of those change, the app treats the reply as out of date.
A reply is saved only if it passes the guardrail check. If it fails, Claude is
asked again, up to 3 more times.

Never calls Open-Meteo. Reads the Claude key from GROUNDTRUTH_CLAUDE_KEY and
never prints or saves it.
"""

import datetime as dt
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import claude_text, replays, risk, weather  # noqa: E402


def main():
    refresh = "--refresh" in sys.argv[1:]
    client = claude_text.make_client(os.environ.get("GROUNDTRUTH_CLAUDE_KEY"))
    if client is None:
        sys.exit("GROUNDTRUTH_CLAUDE_KEY is not set.")
    still_failing = []
    for case in replays.load_replays():
        name = case["name"]
        path = replays.claude_reply_file(name)
        try:
            with weather.offline():
                result = risk.assess(float(case["latitude"]), float(case["longitude"]),
                                     dt.date.fromisoformat(case["date"]))
        except weather.NotAvailable as e:
            print(f"{name}: skipped, replay data not saved ({e})")
            continue
        facts = claude_text.facts(result, replays.place_of(case), dt.date.today(),
                                  replays.SPECIAL_NOTES.get(name))
        if result["level"] not in risk.LEVELS:
            print(f"{name}: Not enough data, so no Claude reply (template mode)")
            continue
        if result["level"] == "Typical":
            if path.exists():
                path.unlink()
                print(f"{name}: Typical: fixed wording, Claude isn't asked (deleted the old {path.name})")
            else:
                print(f"{name}: Typical: fixed wording, Claude isn't asked")
            continue
        if not refresh:
            reply, problems = claude_text.saved_reply(path, facts)
            if reply is not None:
                print(f"{name}: saved reply is up to date and passes the checks")
                continue
            print(f"{name}: {problems[-1]}; asking Claude")
        reply, problems = claude_text.write(facts, client, attempts=claude_text.CACHE_ATTEMPTS,
                                            timeout=claude_text.CACHE_TIMEOUT_S)
        for i, p in enumerate(problems, 1):
            print(f"  try {i} not used: {p}")
        if reply is None:
            still_failing.append((name, problems))
            print(f"{name}: STILL FAILING after {claude_text.CACHE_ATTEMPTS} tries (nothing saved)")
            continue
        tries = len(problems) + 1  # every failed try left one problem
        claude_text.save_reply(path, facts, reply, tries)
        print(f"{name}: saved after {tries} {'try' if tries == 1 else 'tries'} "
              f"({path.relative_to(ROOT)}): {reply['headline']}")

    if still_failing:
        print("\nStill failing (these replays will show template mode):")
        for name, problems in still_failing:
            print(f"- {name}: {problems[-1]}")
        sys.exit(1)
    print("\nEvery raised-day replay has a saved Claude reply that passes the checks (Typical: fixed wording).")


if __name__ == "__main__":
    main()
