# Test log

Last run: 2026-10-23 with `python scripts/replay.py`.
1 case(s) pending: their test day hasn't been picked yet.
Settings: comparison period 1951–1980; the level uses the 30 years before this date; recent rain = 5 days before + the date.

Each check cell shows the wording the app shows, then that check's level. Typical checks show plain wording; the full numbers for every check are in Details.

| Case | Date | Level | Decided by | Rain (24 h) | Feels-like heat | Feels-like cold | Snowfall (24 h) | Wind gust | Recent rain (6-day total) | Expected | Matches? |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Valencia flash flood | 2024-10-29 | **Extreme** | Rain (24 h), Recent rain (6-day total) | not seen in 1951–1980 or in the 30 years before this date; at or above the 150 mm danger line → Extreme | Normal highs for here (feels like up to 20 °C) → Typical | Normal lows for here (feels like down to 17 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 61 km/h; the data misses sudden local storm gusts) → Typical | not seen in 1951–1980 or in the 30 years before this date → Extreme | Extreme rain, possibly beyond the 30-year record | yes |
| Texas Hill Country flood | 2025-07-04 | **High** | Rain (24 h) | about once every 15 years in the 30 years before this date; about as common here as in 1951–1980 → High | Normal highs for here (feels like up to 29 °C) → Typical | Normal lows for here (feels like down to 23 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 50 km/h; the data misses sudden local storm gusts) → Typical | about once every 4.3 years in the 30 years before this date; 3.5 times more common here than in 1951–1980 → Elevated | Elevated or High; forecasts underestimated this rain, so a partial miss is likely | yes |
| Kolkata heat (KK concert) | 2022-05-31 | **High** | Feels-like heat | Normal rain for here (8.2 mm) → Typical | about 48 times a year in the 30 years before this date; 1.4 times more common here than in 1951–1980; at or above the 40 °C danger line → High | Normal lows for here (feels like down to 34 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 28 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (16.5 mm) → Typical | At least High via the heat danger line | yes |
| Bayesian sinking | 2024-08-19 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (2.5 mm) → Typical | Normal highs for here (feels like up to 33 °C) → Typical | Normal lows for here (feels like down to 28 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 45 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (13.8 mm) → Typical | Probably a miss; a sudden local storm is too small for this data | yes |
| Nepal-Tibet glacier-collapse flood | 2026-08-26 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (6.1 mm) → Typical | Normal highs for here (feels like up to 30 °C) → Typical | Normal lows for here (feels like down to 23 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 31 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (65.6 mm) → Typical | Probably Typical or Elevated; a glacier collapse is invisible to weather data | yes |
| Calm control 1, Paiporta | 2024-05-15 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (0.1 mm) → Typical | Normal highs for here (feels like up to 22 °C) → Typical | Normal lows for here (feels like down to 14 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 34 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (0.3 mm) → Typical | Typical | yes |
| Calm control 2, Kolkata | 2022-01-15 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (0.2 mm) → Typical | Normal highs for here (feels like up to 24 °C) → Typical | Normal lows for here (feels like down to 14 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 24 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (17.0 mm) → Typical | Typical | yes |
| Ordinary rain 1, Paiporta (winter) | 2018-02-27 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (15.4 mm) → Typical | Normal highs for here (feels like up to 7 °C) → Typical | Normal lows for here (feels like down to 2 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 58 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (15.7 mm) → Typical | Ordinary rainy day (about 16 mm; 22 mm or more happens about 3 times a year here): Typical or Elevated, not Extreme | yes |
| Ordinary rain 2, Paiporta (autumn) | 2024-09-18 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (15.6 mm) → Typical | Normal highs for here (feels like up to 24 °C) → Typical | Normal lows for here (feels like down to 20 °C) → Typical | No snow forecast → Typical | Normal wind for here (gusts up to 24 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (15.9 mm) → Typical | Ordinary rainy day (about 16 mm; 22 mm or more happens about 3 times a year here): Typical or Elevated, not Extreme | yes |
| Paris snow and cold | 2026-01-07 | **Typical** | Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total) | Normal rain for here (5.1 mm) → Typical | Normal highs for here (feels like up to -1 °C) → Typical | Normal lows for here (feels like down to -6 °C) → Typical | Normal snowfall for here (3.0 cm) → Typical | Normal wind for here (gusts up to 36 km/h; the data misses sudden local storm gusts) → Typical | Normal rain for the last 6 days (10.6 mm) → Typical | Typical. Honest limit: the danger came from snow falling on freezing, unprepared roads. Ice risk and local preparedness aren't checked yet. | yes |
| Ordinary snow, Montreal | — | pending | — | — | — | — | — | — | — | Pending: day not picked yet (scripts/save_replay_data.py picks it). Expect Typical: snow is routine here. | — |

## Claude text (saved replies, kept for Phase 2)

The app doesn't use Claude: every word on the page is written by code. These saved replies (claude-sonnet-5-5) are kept for Phase 2 and still checked: each is valid only if its fingerprint matches the facts, prompt and model, and it passes the guardrail again. Refill with `python scripts/save_claude_replies.py`.

| Replay | Level | Text shown | Claude's headline |
|---|---|---|---|
| Valencia flash flood | Extreme | Claude mode: passes the checks (fingerprint 89ea8edef4a4) | Extreme risk of heavy rain. |
| Texas Hill Country flood | High | Claude mode: passes the checks (fingerprint 0b1a5dc93460) | High risk of heavy rain. |
| Kolkata heat (KK concert) | High | Claude mode: passes the checks (fingerprint c21c2c155716) | High risk of dangerous feels-like heat. |
| Bayesian sinking | Typical | fixed wording (Claude isn't asked on Typical days) | — |
| Nepal-Tibet glacier-collapse flood | Typical | fixed wording (Claude isn't asked on Typical days) | — |
| Calm control 1, Paiporta | Typical | fixed wording (Claude isn't asked on Typical days) | — |
| Calm control 2, Kolkata | Typical | fixed wording (Claude isn't asked on Typical days) | — |
| Paris snow and cold | Typical | fixed wording (Claude isn't asked on Typical days) | — |

## Details

### Valencia flash flood — 2024-10-29

- Level: **Extreme** (decided by: Rain (24 h), Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 39.46, -0.45
- History: Open-Meteo Historical Weather API (ERA5), grid point 39.50, -0.50

| Check | Value | In 1994–2024 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 202.1 mm | not seen in those 30 years (0 days) | not seen in 1951–1980 (0) | not seen in 1951–1980 or in the 30 years before this date | Extreme | 150 mm: crossed | Extreme |
| Feels-like heat | 20.2 °C | about 215 times a year (6443 days) | about 189 times a year (5670) | 1.1 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 17.3 °C | about 226 times a year (6788 days) | about 246 times a year (7383) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 61.2 km/h | about 8.7 times a year (262 days) | about 7.8 times a year (234) | 1.1 times more common here than in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 257.0 mm | not seen in those 30 years (0 spells) | not seen in 1951–1980 (0) | not seen in 1951–1980 or in the 30 years before this date | Extreme | — | Extreme |

- Rain in the 5 days before the date: 54.9 mm (from history (ERA5) for the earlier days); daily amounts: 0.0 mm, 8.8 mm, 15.2 mm, 20.6 mm, 10.3 mm, 202.1 mm
- Shown for Rain (24 h): "not seen in 1951–1980 or in the 30 years before this date; at or above the 150 mm danger line"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 20 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 17 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 61 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "not seen in 1951–1980 or in the 30 years before this date"

### Texas Hill Country flood — 2025-07-04

- Level: **High** (decided by: Rain (24 h))
- Forecast: Open-Meteo Historical Forecast API, grid point 30.07, -99.33
- History: Open-Meteo Historical Weather API (ERA5), grid point 30.00, -99.25

| Check | Value | In 1995–2025 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 106.9 mm | about once every 15 years (2 days) | about once every 15 years (2) | about as common here as in 1951–1980 | High | 150 mm: not crossed | High |
| Feels-like heat | 28.6 °C | about 158 times a year (4731 days) | about 147 times a year (4412) | 1.1 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 23.0 °C | about 275 times a year (8253 days) | about 299 times a year (8976) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 49.7 km/h | about 70 times a year (2089 days) | about 67 times a year (2021) | about as common here as in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 143.6 mm | about once every 4.3 years (7 spells) | about once every 15 years (2) | 3.5 times more common here than in 1951–1980 | Elevated | — | Elevated |

- Rain in the 5 days before the date: 36.7 mm (from history (ERA5) for the earlier days); daily amounts: 0.2 mm, 5.8 mm, 1.2 mm, 11.1 mm, 18.4 mm, 106.9 mm
- Shown for Rain (24 h): "about once every 15 years in the 30 years before this date; about as common here as in 1951–1980"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 29 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 23 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 50 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "about once every 4.3 years in the 30 years before this date; 3.5 times more common here than in 1951–1980"

### Kolkata heat (KK concert) — 2022-05-31

- Level: **High** (decided by: Feels-like heat)
- Forecast: Open-Meteo Historical Forecast API, grid point 22.60, 88.32
- History: Open-Meteo Historical Weather API (ERA5), grid point 22.50, 88.25

| Check | Value | In 1992–2022 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 8.2 mm | about 67 times a year (1999 days) | about 68 times a year (2053) | about as common here as in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 41.3 °C | about 48 times a year (1448 days) | about 34 times a year (1018) | 1.4 times more common here than in 1951–1980 | Typical | 40 °C: crossed | High |
| Feels-like cold | 34.1 °C | about 340 times a year (10196 days) | about 359 times a year (10759) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10957 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 27.7 km/h | about 177 times a year (5310 days) | about 186 times a year (5566) | about as common here as in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 16.5 mm | about 29 times a year (876 spells) | about 29 times a year (879) | about as common here as in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 8.3 mm (from history (ERA5) for the earlier days); daily amounts: 0.9 mm, 0.1 mm, 3.0 mm, 3.7 mm, 0.6 mm, 8.2 mm
- Shown for Rain (24 h): "Normal rain for here (8.2 mm)"
- Shown for Feels-like heat: "about 48 times a year in the 30 years before this date; 1.4 times more common here than in 1951–1980; at or above the 40 °C danger line"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 34 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 28 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (16.5 mm)"

### Bayesian sinking — 2024-08-19

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 38.09, 13.52
- History: Open-Meteo Historical Weather API (ERA5), grid point 38.00, 13.50

| Check | Value | In 1994–2024 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 2.5 mm | about 64 times a year (1935 days) | about 72 times a year (2166) | 1.1 times less common here than in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 32.6 °C | about 57 times a year (1699 days) | about 28 times a year (844) | 2.0 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 27.6 °C | about 327 times a year (9801 days) | about 354 times a year (10628) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 45.0 km/h | about 58 times a year (1736 days) | about 58 times a year (1754) | about as common here as in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 13.8 mm | about 21 times a year (626 spells) | about 24 times a year (718) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 11.3 mm (from history (ERA5) for the earlier days); daily amounts: 0.0 mm, 0.0 mm, 0.4 mm, 0.3 mm, 10.6 mm, 2.5 mm
- Shown for Rain (24 h): "Normal rain for here (2.5 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 33 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 28 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 45 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (13.8 mm)"

### Nepal-Tibet glacier-collapse flood — 2026-08-26

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 28.08, 85.22
- History: Open-Meteo Historical Weather API (ERA5), grid point 28.00, 85.25

| Check | Value | In 1996–2026 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 6.1 mm | about 129 times a year (3873 days) | about 133 times a year (4000) | about as common here as in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 30.1 °C | about 68 times a year (2032 days) | about 21 times a year (634) | 3.2 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 23.0 °C | about 319 times a year (9576 days) | about 354 times a year (10628) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10957 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 30.6 km/h | about 228 times a year (6851 days) | about 214 times a year (6425) | 1.1 times more common here than in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 65.6 mm | about 18 times a year (552 spells) | about 19 times a year (556) | about as common here as in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 59.5 mm (from history (ERA5) for the earlier days); daily amounts: 18.1 mm, 14.4 mm, 3.6 mm, 7.2 mm, 16.2 mm, 6.1 mm
- Shown for Rain (24 h): "Normal rain for here (6.1 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 30 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 23 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 31 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (65.6 mm)"

### Calm control 1, Paiporta — 2024-05-15

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 39.46, -0.45
- History: Open-Meteo Historical Weather API (ERA5), grid point 39.50, -0.50

| Check | Value | In 1994–2024 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 0.1 mm | about 107 times a year (3208 days) | about 132 times a year (3973) | 1.2 times less common here than in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 22.0 °C | about 194 times a year (5806 days) | about 169 times a year (5059) | 1.1 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 14.1 °C | about 189 times a year (5679 days) | about 211 times a year (6319) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 33.8 km/h | about 154 times a year (4624 days) | about 143 times a year (4281) | 1.1 times more common here than in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 0.3 mm | about 45 times a year (1357 spells) | about 51 times a year (1529) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 0.2 mm (from history (ERA5) for the earlier days); daily amounts: 0.0 mm, 0.0 mm, 0.0 mm, 0.0 mm, 0.2 mm, 0.1 mm
- Shown for Rain (24 h): "Normal rain for here (0.1 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 22 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 14 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 34 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (0.3 mm)"

### Calm control 2, Kolkata — 2022-01-15

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 22.60, 88.32
- History: Open-Meteo Historical Weather API (ERA5), grid point 22.50, 88.25

| Check | Value | In 1992–2022 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 0.2 mm | about 186 times a year (5570 days) | about 196 times a year (5885) | 1.1 times less common here than in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 23.6 °C | about 350 times a year (10507 days) | about 351 times a year (10523) | about as common here as in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 14.4 °C | about 42 times a year (1272 days) | about 49 times a year (1469) | 1.2 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 24.5 km/h | about 242 times a year (7268 days) | about 250 times a year (7515) | about as common here as in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 17.0 mm | about 29 times a year (860 spells) | about 29 times a year (870) | about as common here as in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 16.8 mm (from history (ERA5) for the earlier days); daily amounts: 0.0 mm, 3.7 mm, 3.6 mm, 1.2 mm, 8.3 mm, 0.2 mm
- Shown for Rain (24 h): "Normal rain for here (0.2 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 24 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 14 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 24 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (17.0 mm)"

### Ordinary rain 1, Paiporta (winter) — 2018-02-27

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 39.46, -0.45
- History: Open-Meteo Historical Weather API (ERA5), grid point 39.50, -0.50

| Check | Value | In 1988–2018 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 15.4 mm | about 6.2 times a year (185 days) | about 6.6 times a year (199) | 1.1 times less common here than in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 7.1 °C | about 363 times a year (10885 days) | about 358 times a year (10738) | about as common here as in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 1.8 °C | about 18 times a year (543 days) | about 26 times a year (790) | 1.5 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 58.3 km/h | about 10 times a year (300 days) | about 11 times a year (320) | 1.1 times less common here than in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 15.7 mm | about 11 times a year (319 spells) | about 13 times a year (383) | 1.2 times less common here than in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 0.3 mm (from history (ERA5) for the earlier days); daily amounts: 0.3 mm, 0.0 mm, 0.0 mm, 0.0 mm, 0.0 mm, 15.4 mm
- Shown for Rain (24 h): "Normal rain for here (15.4 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 7 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 2 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 58 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (15.7 mm)"

### Ordinary rain 2, Paiporta (autumn) — 2024-09-18

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 39.46, -0.45
- History: Open-Meteo Historical Weather API (ERA5), grid point 39.50, -0.50

| Check | Value | In 1994–2024 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 15.6 mm | about 6.2 times a year (187 days) | about 6.5 times a year (194) | about as common here as in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | 23.5 °C | about 176 times a year (5287 days) | about 151 times a year (4533) | 1.2 times more common here than in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | 19.8 °C | about 255 times a year (7648 days) | about 277 times a year (8296) | 1.1 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 0.0 cm | about 365 times a year (10958 days) | about 365 times a year (10958) | about as common here as in 1951–1980 | Typical | — | Typical |
| Wind gust | 24.5 km/h | about 310 times a year (9297 days) | about 307 times a year (9203) | about as common here as in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 15.9 mm | about 11 times a year (323 spells) | about 13 times a year (378) | 1.2 times less common here than in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 0.3 mm (from history (ERA5) for the earlier days); daily amounts: 0.1 mm, 0.2 mm, 0.0 mm, 0.0 mm, 0.0 mm, 15.6 mm
- Shown for Rain (24 h): "Normal rain for here (15.6 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to 24 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to 20 °C)"
- Shown for Snowfall (24 h): "No snow forecast"
- Shown for Wind gust: "Normal wind for here (gusts up to 24 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (15.9 mm)"

### Paris snow and cold — 2026-01-07

- Level: **Typical** (decided by: Rain (24 h), Feels-like heat, Feels-like cold, Snowfall (24 h), Wind gust, Recent rain (6-day total))
- Forecast: Open-Meteo Historical Forecast API, grid point 48.85, 2.36
- History: Open-Meteo Historical Weather API (ERA5), grid point 48.75, 2.25

| Check | Value | In 1996–2026 (the 30 years before this date) | In 1951–1980 | Compared with 1951–1980 | Rarity level | Danger line | Check level |
|---|---|---|---|---|---|---|---|
| Rain (24 h) | 5.1 mm | about 49 times a year (1463 days) | about 46 times a year (1390) | 1.1 times more common here than in 1951–1980 | Typical | 150 mm: not crossed | Typical |
| Feels-like heat | -0.6 °C | about 350 times a year (10511 days) | about 342 times a year (10251) | about as common here as in 1951–1980 | Typical | 40 °C: not crossed | Typical |
| Feels-like cold | -6.5 °C | about 12 times a year (361 days) | about 19 times a year (582) | 1.6 times less common here than in 1951–1980 | Typical | — | Typical |
| Snowfall (24 h) | 3.0 cm | about 1.1 times a year (34 days) | about 1.3 times a year (40) | 1.2 times less common here than in 1951–1980 | Typical | — | Typical |
| Wind gust | 36.0 km/h | about 172 times a year (5169 days) | about 158 times a year (4729) | 1.1 times more common here than in 1951–1980 | Typical | 100 km/h: not crossed | Typical |
| Recent rain (6-day total) | 10.6 mm | about 33 times a year (1001 spells) | about 34 times a year (1007) | about as common here as in 1951–1980 | Typical | — | Typical |

- Rain in the 5 days before the date: 5.5 mm (from history (ERA5) for the earlier days); daily amounts: 1.8 mm, 0.2 mm, 0.0 mm, 3.5 mm, 0.0 mm, 5.1 mm
- Shown for Rain (24 h): "Normal rain for here (5.1 mm)"
- Shown for Feels-like heat: "Normal highs for here (feels like up to -1 °C)"
- Shown for Feels-like cold: "Normal lows for here (feels like down to -6 °C)"
- Shown for Snowfall (24 h): "Normal snowfall for here (3.0 cm)"
- Shown for Wind gust: "Normal wind for here (gusts up to 36 km/h; the data misses sudden local storm gusts)"
- Shown for Recent rain (6-day total): "Normal rain for the last 6 days (10.6 mm)"

## Replay check: date, level and sentence

Added by the replay-check skill on 2026-10-23. "Previous level" is the level in TESTLOG.md before this run.

| Case | Date | Level | Previous level | Headline shown (code) | Not checked box |
|---|---|---|---|---|---|
| Valencia flash flood | 2024-10-29 | **Extreme** | Extreme | Extreme risk of heavy rain. | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Texas Hill Country flood | 2025-07-04 | **High** | High | High risk of heavy rain. | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Kolkata heat (KK concert) | 2022-05-31 | **High** | High | High risk of dangerous feels-like heat. | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Bayesian sinking | 2024-08-19 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Nepal-Tibet glacier-collapse flood | 2026-08-26 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings, and civil protection and geological authorities. |
| Calm control 1, Paiporta | 2024-05-15 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Calm control 2, Kolkata | 2022-01-15 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Ordinary rain 1, Paiporta (winter) | 2018-02-27 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, ice on roads, landslides, glacier collapse. Follow official weather and storm warnings. |
| Ordinary rain 2, Paiporta (autumn) | 2024-09-18 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Paris snow and cold | 2026-01-07 | **Typical** | Typical | (no headline) Typical for rain, temperature, snow and wind | Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings. |
| Ordinary snow, Montreal | — | pending | pending | — | — |

### Level changes since the last run

None.

### Full output per case

The actual text a person would see, in screen order. Every word on the page is written by code; Claude is switched off (kept for Phase 2), and its saved headline is listed only for reference.

#### Valencia flash flood — 2024-10-29 — Extreme

On the page (every word written by code):

- Level box: "Paiporta, Valencia, Spain · 29 Oct 2024" / **Extreme** / **"About 45% of a year's rain, forecast in one day"** / "202 mm of rain forecast in 24 h, above the 150 mm danger line; 257 mm of rain over 6 days"
- Headline: "Extreme risk of heavy rain."
- Line under the headline: "→ Avoid underpasses, low roads and riverbanks."
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: "How often days like this happen here: in the 30 years before this date, and in 1951–1980, the period scientists use as a baseline for measuring warming."
  - Rain in 24 hours [Extreme] — 202 mm forecast — "Rain like this was never seen here in either period."
  - Rain over 6 days [Extreme] — 257 mm 54.9 mm measured + the day's forecast — "A wet spell like this was never seen here in either period."
- Normal for here (4) (collapsed):
  - Feels-like high  20 °C, normal for here
  - Feels-like low  17 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 61 km/h, normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Paiporta, Valencia, Spain 29 Oct 2024: Extreme risk. Rain 202 mm forecast. Avoid low roads and riverbanks. Check official warnings."

Claude's saved headline (kept for Phase 2, not shown on the page; 1 try; passes the guardrail): "Extreme risk of heavy rain."

#### Texas Hill Country flood — 2025-07-04 — High

On the page (every word written by code):

- Level box: "Texas Hill Country, USA · 4 Jul 2025" / **High** / **"About 16% of a year's rain, forecast in one day"** / "107 mm of rain forecast in 24 h"
- Headline: "High risk of heavy rain."
- Line under the headline: "→ Avoid underpasses, low roads and riverbanks."
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: "How often days like this happen here: in the 30 years before this date, and in 1951–1980, the period scientists use as a baseline for measuring warming."
  - Rain in 24 hours [High] — 107 mm forecast — Now (1995–2025): 2 times in 30 years (bar 0.29); 1951–1980: 2 times in 30 years (bar 0.29)
  - Rain over 6 days [Elevated] — 144 mm 36.7 mm measured + the day's forecast — Now (1995–2025): 7 times in 30 years (bar 1.00); 1951–1980: 2 times in 30 years (bar 0.29)
- Normal for here (4) (collapsed):
  - Feels-like high  29 °C, normal for here
  - Feels-like low  23 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 50 km/h, normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Texas Hill Country, USA 4 Jul 2025: High risk. Rain 107 mm forecast. Avoid low roads and riverbanks. Check official warnings."

Claude's saved headline (kept for Phase 2, not shown on the page; 1 try; passes the guardrail): "High risk of heavy rain."

#### Kolkata heat (KK concert) — 2022-05-31 — High

On the page (every word written by code):

- Level box: "Kolkata, India · 31 May 2022" / **High** / "Feels like 41 °C forecast, above the 40 °C danger line, however often it happens here"
- Headline: "High risk of dangerous feels-like heat."
- Line under the headline: "→ Avoid heavy exertion outdoors, drink water, and check on older or vulnerable people."
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: "How often days like this happen here: in the 30 years before this date, and in 1951–1980, the period scientists use as a baseline for measuring warming."
  - Feels-like heat [High] — 41 °C forecast — Now (1992–2022): about 48 times a year (bar 1.00); 1951–1980: about 34 times a year (bar 0.70)
- Normal for here (5) (collapsed):
  - Rain in 24 hours  8.2 mm, normal for here
  - Feels-like low  34 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 28 km/h, normal for here
  - Rain over 6 days  16 mm (8.3 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Kolkata, India 31 May 2022: High risk. Feels-like 41 C forecast. Avoid exertion, drink water, check on older people. Check official warnings."

Claude's saved headline (kept for Phase 2, not shown on the page; 1 try; passes the guardrail): "High risk of dangerous feels-like heat."

#### Bayesian sinking — 2024-08-19 — Typical

On the page (every word written by code):

- Level box: "Porticello, Sicily, Italy · 19 Aug 2024" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  2.5 mm, normal for here
  - Feels-like high  33 °C, normal for here
  - Feels-like low  28 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 45 km/h, normal for here
  - Rain over 6 days  14 mm (11.3 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Porticello, Sicily, Italy 19 Aug 2024: Typical rain, temperature, snow and wind. Storms, ice, landslides not checked. Check official warnings."

#### Nepal-Tibet glacier-collapse flood — 2026-08-26 — Typical

On the page (every word written by code):

- Level box: "Nepal–Tibet border area · 26 Aug 2026" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings, and civil protection and geological authorities."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  6.1 mm, normal for here
  - Feels-like high  30 °C, normal for here
  - Feels-like low  23 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 31 km/h, normal for here
  - Rain over 6 days  66 mm (59.5 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Nepal-Tibet bo. 26 Aug 2026: Typical rain, temperature, snow and wind. Storms, ice, landslides, glacier floods not checked. Check official warnings."

#### Calm control 1, Paiporta — 2024-05-15 — Typical

On the page (every word written by code):

- Level box: "Paiporta, Valencia, Spain · 15 May 2024" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  0.1 mm, normal for here
  - Feels-like high  22 °C, normal for here
  - Feels-like low  14 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 34 km/h, normal for here
  - Rain over 6 days  0.3 mm (0.2 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Paiporta, Valencia, Spain 15 May 2024: Typical rain, temperature, snow and wind. Storms, ice, landslides not checked. Check official warnings."

#### Calm control 2, Kolkata — 2022-01-15 — Typical

On the page (every word written by code):

- Level box: "Kolkata, India · 15 Jan 2022" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  0.2 mm, normal for here
  - Feels-like high  24 °C, normal for here
  - Feels-like low  14 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 24 km/h, normal for here
  - Rain over 6 days  17 mm (16.8 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Kolkata, India 15 Jan 2022: Typical rain, temperature, snow and wind. Storms, ice, landslides not checked. Check official warnings."

#### Ordinary rain 1, Paiporta (winter) — 2018-02-27 — Typical

On the page (every word written by code):

- Level box: "39.43, -0.42 · 27 Feb 2018" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, ice on roads, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  15 mm, normal for here
  - Feels-like high  7.1 °C, normal for here
  - Feels-like low  1.8 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 58 km/h, normal for here
  - Rain over 6 days  16 mm (0.3 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth 39.43, -0.42 27 Feb 2018: Typical rain, temperature, snow and wind. Storms, ice, landslides not checked. Check official warnings."

#### Ordinary rain 2, Paiporta (autumn) — 2024-09-18 — Typical

On the page (every word written by code):

- Level box: "39.43, -0.42 · 18 Sep 2024" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: not shown
- Normal for here (6) (collapsed):
  - Rain in 24 hours  16 mm, normal for here
  - Feels-like high  24 °C, normal for here
  - Feels-like low  20 °C, normal for here
  - Snow  none forecast
  - Gusts  up to 24 km/h, normal for here
  - Rain over 6 days  16 mm (0.3 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth 39.43, -0.42 18 Sep 2024: Typical rain, temperature, snow and wind. Storms, ice, landslides not checked. Check official warnings."

#### Paris snow and cold — 2026-01-07 — Typical

On the page (every word written by code):

- Level box: "Paris, France · 7 Jan 2026" / **Typical** / "for rain, temperature, snow and wind"
- Headline: none (Typical days have none)
- Line under the headline: "Roads may be icy; ice itself isn't checked."
- Line under the headline: "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm warnings."
- Then and now: "How often days like this happen here: in the 30 years before this date, and in 1951–1980, the period scientists use as a baseline for measuring warming."
  - Snow in 24 hours — 3.0 cm forecast — Now (1996–2026): about 1.1 times a year (bar 0.85); 1951–1980: about 1.3 times a year (bar 1.00) — "Snow like this is rarer here now, so people and places may be less prepared for it."
- Normal for here (5) (collapsed):
  - Rain in 24 hours  5.1 mm, normal for here
  - Feels-like high  -0.6 °C, normal for here
  - Feels-like low  -6.5 °C, normal for here
  - Gusts  up to 36 km/h, normal for here
  - Rain over 6 days  11 mm (5.5 mm measured + the day's forecast), normal for here

Text message (not shown on the page; kept for Phase 2): "Groundtruth Paris, France 7 Jan 2026: Typical rain, temperature, snow and wind. Roads may be icy; ice, storms, landslides not checked. Check official warnings."

Weather data by Open-Meteo.com
