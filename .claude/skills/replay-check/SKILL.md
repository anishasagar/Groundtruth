---
name: replay-check
description: Run Groundtruth's replay check — replays every test case in tests/cases.csv with the saved data, updates TESTLOG.md with the date, level and sentence for each case (plus the full template and Claude text), and lists any case whose level changed since the last run. Use after any change to the risk logic, the template text or the Claude prompt, or when asked to "run the replay", "replay check" or "update the test log".
---

# Replay check

Runs the existing `scripts/replay.py` (never rebuild or edit it) and then adds a summary to TESTLOG.md.
Nothing calls Open-Meteo or Claude: it only uses the saved data in `data/` and the saved Claude replies.

## Steps

1. Make sure the packages are installed. If `python -c "import pandas, requests, anthropic"` fails, run
   `pip install -r requirements.txt`.
2. From the project folder, run:

   ```
   python .claude/skills/replay-check/summarize.py
   ```

   This:
   - reads each case's level from the current TESTLOG.md (the last run) before it is overwritten,
   - runs `scripts/replay.py`, which rewrites TESTLOG.md,
   - adds the section **"Replay check: date, level and sentence"**: one row per case with its date, level,
     previous level, the sentence the app shows (the fixed wording on Typical days; on raised days Claude's
     headline, or the template sentence in template mode) and the template sentence,
   - adds **"Level changes since the last run"** (or "None."),
   - adds **"Full output per case"**, in screen order: what code writes on every day (the level box, the lines
     under it, then and now, the yellow line), the text message (kept in code, not on the page), the
     template-mode headline, and Claude's saved reply (headline, why, confidence note) with how
     many tries it took and whether it still passes the guardrail. The "Claude tries" column shows the tries too.
3. Read the new sections of TESTLOG.md and tell the user, in plain language:
   - each case's level and the sentence shown,
   - any level change since the last run, and why it happened if you know (which change caused it),
   - any row in the main table marked **"no — lower than expected"**, any case that "could not run", and any
     replay now in template mode (its saved Claude reply is out of date or fails the guardrail — refill with
     `python scripts/save_claude_replies.py`, which needs the Claude key).

## Rules

- Never lower a level, or change a case's expectations, just to make a test case pass. If a level went down,
  explain why first and ask the user (CLAUDE.md, "How we build").
- Don't edit `scripts/replay.py`, the risk engine, the prompt or the template text as part of this check.
  This skill only runs, records and reports.
- If the run changed TESTLOG.md, that is the record of this run: commit it with the change that caused it.
