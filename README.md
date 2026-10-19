# Groundtruth

Tells a person, in one plain sentence, how unusual today's weather is for their location compared with its climate-shifted baseline. See `CLAUDE.md` for the project rules.

## Try it

```
pip install -r requirements.txt
python scripts/paiporta.py
```

## The app

```
streamlit run app.py
```

Search a place and date, or pick a **Replay a past event**. Replays never call Open-Meteo: they use the saved history in `data/history/` and the saved forecasts in `data/forecasts/`. To download and save that data (needs Open-Meteo reachable; safe to run again, it continues where it stopped):

```
python scripts/save_replay_data.py
```

Checks on the wording: `python tests/test_message.py`.

## Claude text

Claude (`claude-sonnet-5-5`) writes the headline, what it means, short why bullets, the text message and a confidence note, from the computed facts only (`groundtruth/claude_text.py`). Code checks every reply: the level word, every number, banned words, "normal", the 160-character SMS, 2–4 bullets, and official warnings. If anything fails, or Claude times out or errors, the app shows the template sentence labelled "template mode", with the reason in small print. "Not enough data" days never go to Claude.

The key comes from `st.secrets` or the environment variable `GROUNDTRUTH_CLAUDE_KEY`. Never write it into a file.

Replays never call Claude: they use the saved replies in `data/claude_replies/`, checked again every time. Each one carries a fingerprint of the facts, the prompt and the model; when any of those change, it is out of date and the replay shows template mode until you refill:

```
python scripts/save_claude_replies.py
```

Checks on the Claude text (no API calls): `python tests/test_claude_text.py`.

## Test cases

`tests/cases.csv` lists real events and calm days with the level we expect. Run them all (no Open-Meteo calls; uses only the saved data) and write the results to `TESTLOG.md`:

```
python scripts/replay.py
```

The risk engine is `groundtruth/risk.py`. The time periods (the 1951–1980 comparison and the 30-year window for the level) are in the SETTINGS section at its top.

Downloaded history is saved in `data/history/` (one file per place) and kept in the project, so it isn't downloaded again. Open-Meteo's free service has a daily limit; if it's used up, `scripts/save_replay_data.py` stops and you can run it again the next day.

## Known limitations

- **Past forecasts are short-range.** For past dates we use Open-Meteo's Historical Forecast API. It shows what the models predicted a few hours ahead, not what a forecast issued days ahead said.
- **History is coarser than forecasts.** The 1951-onward history (ERA5) is a ~25 km grid, while forecasts are sharper. A sharp forecast compared with a smoothed history makes today look more extreme, so the comparison leans toward over-warning.

Weather data by Open-Meteo.com
