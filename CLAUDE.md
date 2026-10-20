# Groundtruth — project rules

## What this is
A web app that tells a person, in one plain sentence, how unusual today's weather is for their exact location given how climate change has shifted the local baseline, and what that means for their decision. Phase 1 = climate-adjusted weather risk + plain-language synthesis only.

## Safety rules (non-negotiable)
1. Code computes every number and the risk level. The language model only puts them into words. It may never change the level or add a number that isn't in the facts it was given.
2. Over-warn, never under-warn. The final level is the worse of the relative check (how rare for this place) and the absolute danger lines. When unsure, choose the higher level.
   Absolute danger lines: rain >= 150 mm in 24 h, feels-like >= 40 °C, gust >= 100 km/h. Each line crossed = at least High.
   The recent-rain total (the 5 days before plus the day itself; for future days, the forecast) gets the same rarity check. Recent wet or dry spells can only raise the level, never lower it.
   Cold and snow get the same rarity check. Snow: daily snowfall in cm (how often a day with at least this much snow happened). Cold: the lowest feels-like temperature of the day, checked in the cold direction (how often a day at least this cold happened). No fixed danger lines for cold or snow yet; fixed cold lines need research. Like every check, they can only raise the level.
3. Never use the words "safe", "no risk" or "all clear".
4. If data is missing or thin, say "Not enough data — check official sources". Never fill gaps with guesses.
5. Every assessment points to official warnings. Groundtruth never replaces them.
6. Say what the data can't see: the history data is a ~25 km grid and misses very local storms. Groundtruth covers weather-driven hazards only. For geological hazards (landslides, glacier collapse, earthquakes), point people to local civil protection and geological authorities.
7. Never claim climate change caused an event or made it "X times more likely". That is attribution, which needs climate models. Say only what the data shows: "days like this are X times more common here than in 1951–1980".
8. 'Normal' may only describe what a check measures, compared with the recent 30 years. It never means safe.

## How we build
- Python + Streamlit. Keep it small: streamlit, pandas, requests, anthropic. No other frameworks.
- Data: Open-Meteo (forecast, historical weather, historical forecast, geocoding). No key. Footer: "Weather data by Open-Meteo.com".
- The Claude key is read from st.secrets or the environment variable GROUNDTRUTH_CLAUDE_KEY. Never write keys into files.
- If the Claude call or the guardrail check fails, show the template sentence labelled "template mode".
- Test cases live in tests/cases.csv. After any change to the risk logic or the prompt, run the replay check and update TESTLOG.md.
- Never lower a level just to make a test case pass. Explain why first.
- Time periods (provisional, may change before the demo): the comparison line uses 1951–1980; the level uses the most recent 30 years before the date. Both live in one settings section in the risk engine.
- I'm not a programmer: explain changes in plain language and keep each change small.

## Phase 2 (don't build yet)
- Top priority — Storm heads-up: flag thunderstorm and hail conditions from the forecast (weather codes, CAPE), as an absolute flag because history can't measure storm rarity. Test on the Bayesian and Valencia replays and on ordinary summer storm days. It must use both weather codes and CAPE: the Bayesian forecast showed high CAPE with no thunderstorm codes.
- Ice-risk heads-up: an absolute flag when precipitation falls at or below freezing (Paris 2026-01-07 as the test case).
- Rain and wind: replace the fixed danger lines with location-adaptive ones. Trigger if today's value exceeds the 99th percentile of the 75-year ERA5 record for that location.
- Heat: trigger if today's feels-like value exceeds the location's 99th percentile OR is 40 °C or more. Keep this fixed floor: the human body's heat limit doesn't adapt to local climate, and the percentile itself rises as the climate warms.
- Before building this, print Kolkata's 99th-percentile feels-like value and show it to me.
- From the false-reassurance review:
  - Numbers: check each number in Claude's text against its own check (the value next to that check's name and unit, the rate next to "times a year"), not just against all the facts. Today a danger-line number can pass as a check's value.
  - Geological note on every result, not only the Nepal-Tibet replay. Decide where it goes with the layout.
  - "Not enough data" must not hide a higher reading: keep "Not enough data — check official sources" and add what the checks that did run already reach (for example Elevated).
  - Rounding: round cold values toward colder, show one decimal within about 1 unit of a danger line, and never show a rounded value at or above a line that wasn't crossed.
  - Rare Typical checks: for a check that happens only a few times a year (Paris snow, about 1.1 times a year), show how often it happens instead of "Normal…". Don't lower anything.
