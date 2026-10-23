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

Search a place (then pick it under **Which place?**, most populated first) and a date, or pick **Or replay a past event**, which fills in the replay's place and date (changing either switches the replay off). For today or later, a live search also shows the next 48 hours, every 3 hours (never on replays or past dates; hidden if the hourly forecast can't be fetched). Replays never call Open-Meteo: they use the saved history in `data/history/` and the saved forecasts in `data/forecasts/`. To download and save that data (needs Open-Meteo reachable; safe to run again, it continues where it stopped):

```
python scripts/save_replay_data.py
```

Checks on the wording: `python tests/test_message.py`. Checks on the page itself (every replay): `python tests/test_page.py`.

## Claude text (switched off, kept for Phase 2)

Every word on the page is written by code (`groundtruth/message.py`), including the raised-day headline ("High risk of dangerous feels-like heat."). Claude (`groundtruth/claude_text.py`) was tested for the headline and switched off because its wording kept drifting towards reassurance; the app never calls it. If Claude text comes back, it must be shown in purple with a small "written by Claude" label (CLAUDE.md rule 9).

The prompt, the guardrail (`claude_text.check_reply`), its tests and the saved replies in `data/claude_replies/` are kept for Phase 2. The tests still check them (no API calls): `python tests/test_claude_text.py`. To refill the saved replies (needs `GROUNDTRUTH_CLAUDE_KEY`): `python scripts/save_claude_replies.py`.

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
