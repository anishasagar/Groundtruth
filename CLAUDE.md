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
  - Count snow or rain in the days before, not just the day itself (a dry freezing day after snow gets no ice note today).
  - Re-save the Paris forecast with air temperature (temperature_2m_min), so the live path of the ice note is tested; today Paris only gets it through the feels-like low.
- Rain and wind: replace the fixed danger lines with location-adaptive ones. Trigger if today's value exceeds the 99th percentile of the 75-year ERA5 record for that location.
- Heat: trigger if today's feels-like value exceeds the location's 99th percentile OR is 40 °C or more. Keep this fixed floor: the human body's heat limit doesn't adapt to local climate, and the percentile itself rises as the climate warms.
- Before building this, print Kolkata's 99th-percentile feels-like value and show it to me.
- From the false-reassurance review:
  - Numbers: check each number in Claude's text against its own check (the value next to that check's name and unit, the rate next to "times a year"), not just against all the facts. Today a danger-line number can pass as a check's value, and a dropped minus sign can pass ("down to 6 °C" for −6, because "6" appears elsewhere in the facts).
  - Geological note on every result, not only the Nepal-Tibet replay. Decide where it goes with the layout.
  - "Not enough data" must not hide a higher reading: keep "Not enough data — check official sources" and add what the checks that did run already reach (for example Elevated).
  - Rounding: round cold values toward colder, show one decimal within about 1 unit of a danger line, and never show a rounded value at or above a line that wasn't crossed.
  - Rare Typical checks: for a check that happens only a few times a year (Paris snow, about 1.1 times a year), show how often it happens instead of "Normal…". Don't lower anything.
  - Ice in Claude's facts: when the ice note applies, give it to Claude and require "ice" in the confidence note (Paris's confidence note doesn't mention ice today).
  - Text message on Elevated or higher days: when a storm or geological note applies, still add "Storms, landslides, glacier floods not checked." (drop the number, then the place, to make room).
  - Ice note after a wet spell: also trigger it when the 5 days before had rain or snow and the day drops to +1 °C or below (refreezing slush, black ice).
  - Invented descriptions and permission phrases: reject season and month words ("winter", "January", "this time of year") and phrases like "OK to", "good to go", "good day for", "can proceed", "don't need", "not necessary".
  - Confidence note meaning: require "misses" next to "local storm(s)" and "can be too low" next to "forecast"; reject "reliable", "accurate", "confident", "certain", "high confidence".
  - Climate wording: also reject "climate" on its own, "more/less probable", "odds", "fuelled by", "linked to", "sign of".
  - More softening words on Elevated or higher: "scattered", "short-lived", "passing", "patchy", "modest", "marginal(ly)", "borderline", "barely", "merely".
  - Past tense for the day itself: reject "fell", "reached", "was recorded" in sentences about the day's own value (prompt-only today).
  - Danger-line rate: any bullet that gives a danger-line check's yearly rate must also say "danger line" (Kolkata's second bullet stands alone today).
  - Ice note first on Typical days, before the not-covered list.
  - TESTLOG label: "what it means" is shown with Claude's text only, not in template mode; fix the "Full output per case" label.
  - Shortened place names in text messages: cut at a word boundary and separate the place from the date ("Nepal-Tibet bo. 26 Aug 2026", "39.43, -0.42 27 Feb 2018").
  - Prompt typo: an extra quote mark before "minimal risk" in rule 3.
  - (High) Typical headline with ice: when the ice note applies, the fixed Typical headline should start with the warning, e.g. "Roads may be icy. Typical rain, temperature, snow and wind for here. Ice isn't checked, nor are thunderstorms, landslides or glacier collapse." Today the Paris headline only lists ice among things not checked; the text message does say "Roads may be icy".
  - (High) Hazard denials on raised days still pass in other forms: reject an unchecked hazard followed within a few words by "not / isn't / aren't / won't" + "expected / forecast / likely / seen / a concern" ("Thunderstorms are not forecast"); "none" or "nothing" pointing back to a hazard ("nothing to suggest flooding", "but none are forecast" in the confidence note); allow more words between "no" and the hazard; add lightning, tornado, waterspout, squall, downburst, sleet, wildfire, smoke, earthquake, mudslide, debris flow, outburst to the hazard list.
  - Risk play-downs: treat chance, likelihood, danger and threat like "risk"; add "small", "lower", "reduced", "limited" in both word orders; reject "not (a / at) risk", "without (any) risk", "not a concern", "no problem", "harmless"; on raised days reject "not" or "far from" before any level word in any case.
  - "Less common now" in other words: trigger the rule on "more often/frequent/common" with the comparison period, "back then", "then", "during" or "in the past"; reject "less severe", "less dangerous", "less intense", "less extreme", "not as serious/severe".
  - Typical caption: "reviewed in advance" can read as "someone checked today". Consider "This is the same standard wording used on every Typical day. It doesn't know about anything the checks below can't see."
  - Prompt rule 6 still suggests "Typical rain, temperature, snow and wind", which the guardrail rejects on raised days; remove it, and add "not expected", "not forecast", "not likely" to rule 3's examples.
  - TESTLOG: for Typical cases, label the template-mode block "not shown in the app" (or drop it) and list the screen order instead.
  - All-clear rule: "Everything else looks fine." passes; the rule only catches "everything looks fine" (allow "else").
- From the review of the new page layout (no Critical findings):
  - (High) Raised days hide what the data can't see: "forecast can be too low", "misses very local storms", geological hazards and the "Some data was missing" note are only in collapsed sections. Add one always-visible line on every result next to the yellow line (forecast can be too low, misses very local storms, not checked: thunderstorms, hail, ice, wildfire, coastal flooding, landslides, glacier collapse; geological hazards: local civil protection), and show "Some data was missing" visibly.
  - (High) A second crossed danger line can be invisible: the level line names only the checks that set the level, and there is one action line. Show every crossed danger line visibly, each with its action line (e.g. Extreme rain plus 110 km/h gusts).
  - (High) Typical ice line: "Snow or rain on freezing ground can make roads icy." reads as a general fact and is plain text. Tie it to the day and make it stand out: "Roads may be icy: snow or rain is forecast with temperatures near freezing. Ice isn't checked."
  - Hourly strip: no wind shown; the temperature is the first hour of each block, not the hottest or coldest; freezing rain tomorrow gets no ice note (the ice note only covers the assessed date).
  - Live searches never get the bold geological note (only the Nepal-Tibet replay does); covered by the always-visible line above.
  - Search results with identical labels: choosing the second shows the first place. Add coordinates to repeated labels and select by position.
  - Yellow line: consider starting with "Follow official weather warnings." and moving it right under the lines below the level box.
  - "Rarer here now" on trivial Typical checks (Paiporta calm control: a 6-day total of a few tenths of a mm): on Typical days show it only for checks that happen a few times a year. Don't lower anything.
  - Captions: "didn't pass the wording checks" and "wording checked by code" (the page also uses "checks" for the weather checks).
  - "Then and now" caption uses amount(), so 149.6 mm would show as "150 mm" (see the rounding item above).
  - TESTLOG "Template sentence" column for Typical cases still shows the old Typical headline and ICE_NOTE, which aren't on the page.
