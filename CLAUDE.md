Groundtruth — project rules
What this is
A web app that tells a person, in one plain sentence, how unusual today's weather is for their exact location given how climate change has shifted the local baseline, and what that means for their decision. 

Phase 1 = climate-adjusted weather risk + plain-language synthesis only.

Safety rules (non-negotiable)
Code computes every number and the risk level. The language model only puts them into words. It may never change the level or add a number that isn't in the facts it was given.
Over-warn, never under-warn. The final level is the worse of the relative check (how rare for this place) and the absolute danger lines. When unsure, choose the higher level.
Absolute danger lines: rain >= 150 mm in 24 h, feels-like >= 40 °C, gust >= 100 km/h. Each line crossed = at least High.

Never use the words "safe", "no risk" or "all clear".
If data is missing or thin, say "Not enough data — check official sources". Never fill gaps with guesses.
Every assessment points to official warnings. Groundtruth never replaces them.
Say what the data can't see: the history data is a ~25 km grid and misses very local storms. Groundtruth covers weather-driven hazards only. For geological hazards (landslides, glacier collapse, earthquakes), point people to local civil protection and geological authorities.
Never claim climate change caused an event or made it "X times more likely". That is attribution, which needs climate models. Say only what the data shows: "days like this are X times more common here than in 1951–1980".
How we build
Python + Streamlit. Keep it small: streamlit, pandas, requests, anthropic. No other frameworks.
Data: Open-Meteo (forecast, historical weather, historical forecast, geocoding). No key. Footer: "Weather data by Open-Meteo.com".
The Claude key is read from st.secrets or the environment variable GROUNDTRUTH_CLAUDE_KEY. Never write keys into files.
If the Claude call or the guardrail check fails, show the template sentence labelled "template mode".
Test cases live in tests/cases.csv. After any change to the risk logic or the prompt, run the replay check and update TESTLOG.md.
Never lower a level just to make a test case pass. Explain why first.
I'm not a programmer: explain changes in plain language and keep each change small.

Phase 2 (don't build yet)
Rain and wind: replace the fixed danger lines with location-adaptive ones. Trigger if today's value exceeds the 99th percentile of the 75-year ERA5 record for that location.
Heat: trigger if today's feels-like value exceeds the location's 99th percentile OR is 40 °C or more. Keep this fixed floor: the human body's heat limit doesn't adapt to local climate, and the percentile itself rises as the climate warms.
Before building this, print Kolkata's 99th-percentile feels-like value and show it to me.
