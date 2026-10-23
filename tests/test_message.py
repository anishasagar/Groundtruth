"""Checks on the plain-language text. Run from the project folder:  python tests/test_message.py

1. Every case in tests/cases.csv in replay mode (no Open-Meteo). Cases whose data
   isn't saved yet are listed as skipped.
2. Made-up places run through the real risk engine (made-up history and forecast,
   no Open-Meteo), to test the cold and snow checks and the "normal" wording.
3. A "Not enough data" case.
All check the rules in CLAUDE.md.
"""

import datetime as dt
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import geocode, message, replays, risk, weather  # noqa: E402

FORBIDDEN = re.compile(r"\bsafe\b|\bsafely\b|\bsafety\b|\bno risk\b|\ball clear\b|\bcaused\b", re.I)
# "Normal" may only describe what a check measures (CLAUDE.md rule 8): "Normal rain for here", or right after a
# check's value in "The numbers" ("Gusts: up to 28 km/h forecast, normal for here.").
ALLOWED_NORMAL = re.compile(r"Normal (rain for here|rain for the last|temperatures for here|highs for here|"
                            r"lows for here|snowfall for here|wind for here)|normal for here\.$")


def check_text(label, result, texts):
    for t in texts:
        assert not FORBIDDEN.search(t), f"{label}: forbidden wording in: {t}"


def check_result(label, result, place="Somewhere, Far Away Land", special=None):
    today = dt.date.today()
    title = message.headline(result)
    numbers = message.number_lines(result, today)
    sms = message.sms_text(result, place, special)
    meaning = message.what_it_means(result, special)
    check_text(label, result, [title or "", sms, meaning, message.level_line(result), *numbers])
    for t in [meaning, *numbers]:
        for m in re.finditer(r"\bnormal\b", t, re.I):
            assert ALLOWED_NORMAL.match(t, m.start()), f"{label}: 'normal' used outside a check: {t}"
        # Less common than in the past must not sound reassuring.
        assert "less common" not in t, f"{label}: reassuring 'less common' wording: {t}"
    # "The numbers": one plain line per check, in the engine's order, each starting with its label.
    for c, line in zip(result["checks"], numbers):
        assert line.startswith(message.NUMBER_LABEL[c["key"]].split(" {")[0]), f"{label}: {line}"
        if c.get("crosses_danger_line"):
            assert f"the {c['danger_line']} {c['unit']} danger line" in line, f"{label}: {line}"
        assert "**" not in line and "ERA5" not in line, f"{label}: {line}"
    assert len(numbers) >= len(result["checks"]), f"{label}: a check is missing from the numbers"

    # The yellow "Not checked" box is last on every result, and the page's one visible pointer to official warnings.
    lines = message.summary_lines(result, special)
    ice = message.ice_note(result)
    low = message._value(result, "feels_like_min_c")
    cold = low is None or low <= message.ICE_MENTION_AT_OR_BELOW_C
    box = message.NOT_CHECKED.format(ice=message.NOT_CHECKED_ICE if cold and not ice else "")
    if special == "geological":
        box += " " + message.NOT_CHECKED_GEOLOGICAL
    assert lines[-1] == box == message.not_checked(result, special), f"{label}: {lines}"
    assert " ".join(lines).lower().count("official") == 1, f"{label}: official warnings said more than once: {lines}"
    assert message.OFFICIAL_LINE not in " ".join(lines), label
    assert len(re.findall(r"\bice\b", " ".join(lines).lower())) <= 1, f"{label}: ice twice: {lines}"
    assert " ".join(lines).lower().count("thunderstorm") == 1, f"{label}: thunderstorms said twice: {lines}"
    action = message.action_line(result) if result["level"] in risk.LEVELS else None
    expect = ([message.ARROW + action] if action else []) + ([message.ICE_SMS] if ice else [])
    assert lines == expect + [box], f"{label}: {lines}"
    assert not re.search(r"\d", meaning), f"{label}: a number in the headline or the lines under it: {meaning}"

    assert "official" in sms.lower(), f"{label}: SMS must point to official warnings"
    assert len(sms) <= 160, f"{label}: SMS is {len(sms)} characters"
    assert sms.isascii(), f"{label}: SMS should be plain ASCII"
    assert len(message.sms_text(result, "A" * 300, special)) <= 160, f"{label}: SMS too long with a long place name"
    # A Typical SMS says what is typical, never "Typical weather" (also with a very long place name).
    # It always says what isn't checked; any other level always carries its short action. Neither is dropped.
    typical = result["level"] == "Typical"
    for s in (sms, message.sms_text(result, "A" * 300, special)):
        assert "Typical weather" not in s and "Typical risk" not in s, f"{label}: {s}"
        assert ("Typical rain, temperature, snow and wind" in s) == typical, f"{label}: {s}"
        # Always the sender and the date, so a forwarded message can't read as today's.
        assert s.startswith("Groundtruth ") and message._ascii(message.day_text(result["date"])) in s, f"{label}: {s}"
        if typical:  # what isn't checked, said once: storms, ice and landslides (+ glacier floods for the note)
            low_s = s.lower()
            assert all(re.search(rf"\b{w}\b", low_s) for w in ("storms", "ice", "landslides", "not checked")), s
            assert ("glacier floods not checked" in s) == (special == "geological"), f"{label}: {s}"
            assert len(re.findall(r"\bice\b", low_s)) == 1 and "Roads may be icy." not in s, f"{label}: ice twice: {s}"
        else:
            assert "landslides" not in s, f"{label}: {s}"
        if result["level"] in risk.LEVELS[1:] and message.sms_action(result):
            assert message.sms_action(result) in s, f"{label}: short action dropped: {s}"
        assert ("Roads may be icy" in s) == bool(ice), f"{label}: ice note in the SMS: {s}"
    for b in numbers:
        assert not ("danger line" in b and "common here" in b), f"{label}: danger line day called common: {b}"

    if result["level"] in risk.LEVELS:
        # The headline (raised days only), written by code from the check that set the level.
        assert_headline(label, result)
        assert re.search(rf"\b{result['level']}\b", sms), f"{label}: SMS level word does not match"
        if typical:
            assert message.level_line(result) == message.TYPICAL_LEVEL_LINE, label
        else:
            # The value that set the level, with its danger line when crossed ("however often" when it set the level).
            for c in result["checks"]:
                if c["name"] in result["decided_by"]:
                    value = message.LEVEL_VALUE[c["key"]].format(v=message.amount(c["value"], c["unit"]))
                    assert value in message.level_line(result), f"{label}: {message.level_line(result)}"
                    if c.get("crosses_danger_line"):
                        assert f"{c['danger_line']} {c['unit']} danger line" in message.level_line(result), label
            assert ("however often it happens here" in message.level_line(result)) == any(
                message.danger_line_set_level(c) for c in result["checks"] if c["name"] in result["decided_by"])
        # "Then and now": the check that set the level (Typical: only if it happens < 5 times a year now).
        blocks = message.then_and_now(result)
        deciding = message.deciding_check(result)
        shown = not typical or deciding["recent"]["per_year"] < message.THEN_AND_NOW_TYPICAL_BELOW_PER_YEAR
        assert bool(blocks) == shown, f"{label}: then and now shown {bool(blocks)}"
        assert not blocks or blocks[0]["check"] is deciding, label
        assert len(blocks) <= (1 if typical else 2), label
        for block in blocks:
            c = block["check"]
            assert [r["label"] for r in block["rows"]] == [f"Now ({result['recent_label']})", result["baseline_label"]]
            assert max(r["width"] for r in block["rows"]) in (0.0, 1.0)
            events = c["recent"]["count"] + c["baseline"]["count"]
            few = min(c["recent"]["count"], c["baseline"]["count"]) < message.ENOUGH_EVENTS
            assert block["counts"] == few, label
            for r, period, never in ((block["rows"][0], c["recent"], c["recent_text"]),
                                     (block["rows"][1], c["baseline"], c["baseline_text"])):
                if not period["count"]:  # "not seen in …" stays as the engine says it
                    assert r["words"] == never, r
                elif few:  # few events: counts, not rates
                    assert re.fullmatch(r"(once|\d+ times) in \d+ years", r["words"]), r
                else:
                    assert r["words"] == never, r  # the engine's rate
            assert (block["rarer_now"] is not None) == (message.less_common_now(c) and events >= message.ENOUGH_EVENTS)
            # The title names the check and carries its value.
            assert block["title"].startswith(message.THEN_AND_NOW_TITLE[c["key"]] + ": "), block["title"]
            if c["key"] == risk.RECENT_RAIN_KEY:  # part measured, part forecast: never just "forecast"
                assert block["title"].endswith("plus the day's forecast)"), block["title"]
            else:
                assert block["title"].endswith(f": {message.amount(c['value'], c['unit'])} forecast"), block["title"]
        if len(blocks) == 2:  # only when the first has too few, and only a raised check with enough
            first, second = blocks[0]["check"], blocks[1]["check"]
            assert first["recent"]["count"] + first["baseline"]["count"] < message.ENOUGH_EVENTS, label
            assert second["level"] in risk.LEVELS[1:], label
    else:
        assert message.headline(result) is None and "official sources" in message.level_line(result), label
        assert risk.NOT_ENOUGH_TEXT.replace("—", "-") in sms
        assert message.then_and_now(result) == []


def assert_headline(label, result):
    """"<Level> risk of <hazard>." on raised days, from the check that set the level; none on Typical days."""
    title = message.headline(result)
    if result["level"] == "Typical":
        assert title is None, f"{label}: a headline on a Typical day: {title}"
        return
    c = message.deciding_check(result)
    danger = c.get("crosses_danger_line") and message.HAZARD_DANGER_LINE.get(c["key"])
    assert title == f"{result['level']} risk of {danger or message.HAZARD[c['key']]}.", f"{label}: {title}"
    assert not re.search(r"\d", title) and not any(w in title for w in risk.LEVELS if w != result["level"]), title


def not_enough_result():
    checks = [{"key": "rain_mm", "name": "Rain (24 h)", "unit": "mm", "value": None, "level": risk.NOT_ENOUGH,
               "text": risk.NOT_ENOUGH_TEXT, "notes": []}]
    checks.append({**checks[0], "key": "recent_rain_mm", "name": risk.RECENT_RAIN_NAME,
                   "before_total": None, "daily_amounts": [None] * 6, "source": "forecast"})
    return {"level": risk.NOT_ENOUGH, "date": dt.date(2025, 1, 1), "checks": checks, "decided_by": [],
            "baseline_label": risk.baseline_label(), "recent_label": "1995–2024", "notes": []}


# ---- made-up places, run through the real engine ----------------------------

FAKE_DATE = dt.date(2024, 12, 15)


def fake_history():
    """75 years of made-up daily weather. Cold days were more common before 1981."""
    dates = pd.date_range("1951-01-01", FAKE_DATE - dt.timedelta(days=1), freq="D")
    rng = np.random.default_rng(1)
    season = np.cos(2 * np.pi * (dates.dayofyear - 15) / 365)  # 1 in mid-January
    warming = np.where(dates.year < 1981, -3.0, 0.0)
    lows = 5 - 10 * season + warming + rng.normal(0, 4, len(dates))
    snowy = (season > 0.6) & (rng.random(len(dates)) < 0.15)
    return pd.DataFrame({
        "date": dates,
        "rain_mm": np.round(rng.exponential(2, len(dates)), 1),
        "feels_like_max_c": np.round(lows + 9 + rng.normal(0, 2, len(dates)), 1),
        "feels_like_min_c": np.round(lows, 1),
        "snow_cm": np.where(snowy, np.round(rng.uniform(1, 6, len(dates)), 1), 0.0),
        "gust_max_kmh": np.round(rng.gamma(6, 5, len(dates)), 1),
    })


def fake_assess(**forecast):
    """risk.assess on the made-up history with this forecast (no Open-Meteo)."""
    hist = fake_history()
    values = {"rain_mm": 1.0, "feels_like_max_c": 12.0, "feels_like_min_c": 3.0, "snow_cm": 0.0,
              "gust_max_kmh": 25.0, **forecast}
    grid = {"latitude": 0.0, "longitude": 0.0}
    old = risk.get_forecast_day, risk.get_history
    risk.get_forecast_day = lambda lat, lon, date, today=None: {"source": "made up", "grid_point": grid, **values}
    risk.get_history = lambda lat, lon, start, end: {"source": "made up", "grid_point": grid, "data": hist}
    try:
        return risk.assess(0.0, 0.0, FAKE_DATE, today=dt.date(2026, 1, 1)), hist
    finally:
        risk.get_forecast_day, risk.get_history = old


def check(result, key):
    return next(c for c in result["checks"] if c["key"] == key)


def made_up_cases():
    # Everything ordinary: the Typical headline, one merged temperature line, "No snow forecast".
    r, _ = fake_assess()
    check_result("made up: ordinary", r)
    numbers = message.number_lines(r, dt.date(2026, 1, 1))
    assert r["level"] == "Typical", r["level"]
    assert message.headline(r) is None  # Typical days have no headline
    assert message.level_line(r) == "for rain, temperature, snow and wind"
    assert message.ice_note(r) is None and message.ice_line(r) is None  # 1 mm of rain, above freezing
    assert "Snow: none forecast." in numbers, numbers
    assert numbers[0] == "Rain on 15 Dec 2024: 1.0 mm forecast, normal for here.", numbers[0]
    assert numbers[1] == "Feels-like high: 12 °C forecast, normal for here.", numbers[1]
    assert numbers[2] == "Feels-like low: 3.0 °C forecast, normal for here.", numbers[2]
    assert numbers[5].startswith("Rain over 6 days: ") and numbers[5].endswith(", normal for here."), numbers[5]
    assert message.number_lines(r, FAKE_DATE)[0] == "Rain today: 1.0 mm forecast, normal for here.", "today's wording"
    assert message.then_and_now(r) == []  # every check happens 5 or more times a year: no Then and now
    assert message.summary_lines(r) == [  # feels-like low 3 °C: ice on roads is listed
        "Not checked: thunderstorms, ice on roads, landslides, glacier collapse. Follow official weather and storm "
        "warnings."], message.summary_lines(r)
    print("ok: made up: ordinary day -> Typical")

    # A rare cold day: raises the level, cold action line, and "less common now" isn't reassuring.
    _, hist = fake_assess()
    recent = hist[hist["date"].dt.year >= 1994]["feels_like_min_c"].sort_values()
    r, _ = fake_assess(feels_like_min_c=float(recent.iloc[6]))  # about 7 days this cold in 30 years
    check_result("made up: rare cold", r)
    cold = check(r, "feels_like_min_c")
    assert r["level"] in ("Elevated", "High", "Extreme") and cold["level"] == r["level"], (r["level"], cold["level"])
    assert cold["ratio"] is not None and cold["ratio"] < 1, cold["ratio_text"]
    assert message.summary_lines(r)[0] == message.ARROW + message.ACTIONS["cold"]
    assert message.headline(r) == f"{r['level']} risk of extreme cold.", message.headline(r)
    first = message.number_lines(r)[2]
    assert first.startswith("Feels-like low: ") and ", down from about " in first and " in 1951–1980." in first, first
    assert message.level_line(r).startswith("Feels as cold as "), message.level_line(r)
    rarity = message.then_and_now(r)[0]
    assert rarity["name"] == "Feels-like cold" and rarity["title"].startswith("Feels-like cold: "), rarity
    assert rarity["rarer_now"] == ("Cold like this is rarer here now, so people and places may be less prepared "
                                   "for it."), rarity
    print(f"ok: made up: rare cold -> {r['level']}\n    {first}")

    # Heat over the danger line with ordinary cold: two lines, never "normal temperatures".
    r, _ = fake_assess(feels_like_max_c=41.0)
    check_result("made up: heat", r)
    assert r["level"] in ("High", "Extreme")
    assert message.level_line(r).startswith("Feels like 41 °C forecast, above the 40 °C danger line"), r
    assert message.headline(r) == f"{r['level']} risk of dangerous feels-like heat.", message.headline(r)
    print(f"ok: made up: heat -> {r['level']}")

    # Routine snow: Typical, with the snowfall wording.
    r, _ = fake_assess(snow_cm=2.0)
    check_result("made up: routine snow", r)
    assert check(r, "snow_cm")["level"] == "Typical" and r["level"] == "Typical", check(r, "snow_cm")
    assert message.number_lines(r)[3] == "Snow: 2.0 cm forecast, normal for here.", message.number_lines(r)[3]
    print("ok: made up: routine snow -> Typical")

    # Snow far beyond the record: Extreme, snow action line, snow "how often" caption.
    r, _ = fake_assess(snow_cm=30.0)
    check_result("made up: record snow", r)
    assert r["level"] == "Extreme" and message.summary_lines(r)[0] == message.ARROW + message.ACTIONS["snow"]
    assert message.headline(r) == "Extreme risk of heavy snow."
    assert message.then_and_now(r)[0]["title"] == "Snow in 24 hours: 30 cm forecast", message.then_and_now(r)[0]
    print("ok: made up: record snow -> Extreme")

    # The ice note uses the lower of the day's lowest air temperature and its feels-like low, at +1 °C or below.
    r, _ = fake_assess(snow_cm=2.0, feels_like_max_c=2.0, air_min_c=-5.0)  # +2 °C by day, -5 °C overnight, snow
    check_result("made up: snow, +2 by day, -5 overnight", r)
    assert message.ice_note(r) == message.ICE_NOTE, "a day that drops to -5 °C with snow must get the ice note"
    assert message.ICE_SMS in message.summary_lines(r) and "Roads may be icy" in message.sms_text(r, "Somewhere")
    assert "ice on roads" not in message.not_checked(r), "the ice box already says it"
    assert message.ice_line(r) == "Roads may be icy; ice itself isn't checked."  # its own line under the headline
    r, _ = fake_assess(snow_cm=2.0, feels_like_max_c=2.0, feels_like_min_c=-5.0)  # no air temperature saved
    check_result("made up: snow, feels-like low -5, no air temperature", r)
    assert message.ice_note(r) == message.ICE_NOTE, "falls back to the feels-like low"
    r, _ = fake_assess(rain_mm=3.0, feels_like_min_c=-3.0, air_min_c=1.0)  # the lower of the two: -3
    check_result("made up: rain, air low +1, feels-like low -3", r)
    assert message.ice_note(r) == message.ICE_NOTE, "uses the lower of the air low and the feels-like low"
    r, _ = fake_assess(rain_mm=3.0, feels_like_min_c=-2.0, air_min_c=3.0)
    assert message.ice_note(r) == message.ICE_NOTE, "air +3 °C but feels-like low -2 °C: the lower one counts"
    r, _ = fake_assess(rain_mm=3.0, feels_like_min_c=4.0, air_min_c=0.5)  # just above freezing: the +1 °C margin
    check_result("made up: rain, air low +0.5", r)
    assert message.ice_note(r) == message.ICE_NOTE, "+1 °C margin"
    r, _ = fake_assess(rain_mm=3.0, feels_like_min_c=4.0, air_min_c=1.0)
    assert message.ice_note(r) == message.ICE_NOTE, "exactly +1 °C counts"
    r, _ = fake_assess(rain_mm=3.0, feels_like_min_c=3.0, air_min_c=2.0)
    assert message.ice_note(r) is None, "air +2 °C and feels-like low +3 °C: no ice note"
    r, _ = fake_assess(rain_mm=0.0, air_min_c=-5.0)  # freezing, but nothing falls
    check_result("made up: dry and freezing", r)
    assert message.ice_note(r) is None, "no snow or rain, no ice note"
    r, _ = fake_assess(rain_mm=2.0, air_min_c=0.0)  # exactly 0 °C counts
    assert message.ice_note(r) == message.ICE_NOTE
    # Ice and the glacier note together still fit, with the sender and the date.
    r, _ = fake_assess(snow_cm=2.0, air_min_c=-5.0)
    check_result("made up: snow, freezing, glacier note", r, special="geological")
    for place in ("Nepal-Tibet border area", "A" * 300):
        text = message.sms_text(r, place, "geological")
        assert len(text) <= 160 and "glacier floods" in text and "icy" in text, text
    print("ok: made up: ice note (lower of air and feels-like low, +1 °C margin)")

    # A danger-line day that was more frequent in 1951–1980: "down from", never "less common".
    c = {"key": "feels_like_max_c", "name": "Feels-like heat", "unit": "°C", "value": 41.0, "danger_line": 40,
         "crosses_danger_line": True, "relative_level": "Typical", "level": "High", "ratio": 0.8,
         "recent": {"count": 600, "per_year": 20.0}, "baseline": {"count": 750, "per_year": 25.0},
         "recent_text": "about 20 times a year", "baseline_text": "about 25 times a year",
         "ratio_text": "1.2 times less common here than in 1951–1980", "notes": []}
    line = message.number_lines({"date": FAKE_DATE, "checks": [c], "baseline_label": "1951–1980",
                                 "notes": list(risk.ALWAYS_NOTES)}, FAKE_DATE)[0]
    assert line == ("Feels-like high: 41 °C forecast, above the 40 °C danger line. About 20 days a year here, "
                    "down from about 25 days a year in 1951–1980."), line
    print("ok: danger-line number line when it was more frequent before")

    # The scope line names what we don't check.
    for word in ("thunderstorms", "hail", "freezing rain", "wildfire", "air quality", "coastal flooding",
                 "geological"):
        assert word in message.SCOPE_LINE, word
    assert len(message.HOW_SURE_LINES) == 4 and message.HOW_SURE_LINES[0] == message.OFFICIAL_LINE
    for word in ("25 km", "local storms", "too low", "civil protection and geological authorities"):
        assert word in " ".join(message.HOW_SURE_LINES), word
    assert "Thunderstorms are not checked" in message.STORM_NOTE
    assert message.OFFICIAL_LINE == "Check your official weather warnings. Groundtruth never replaces them."
    print("ok: scope line, storm note and How sure are we")


def hourly_cases():
    """The 48-hour strip from a made-up hourly forecast (no Open-Meteo)."""
    times = pd.date_range("2026-10-21 00:00", periods=72, freq="h")
    rain = [0.0] * 72
    rain[16], rain[17] = 0.4, 1.1  # 16:00 and 17:00 -> the 15:00 slot
    codes = [1] * 72
    codes[16] = 95  # a thunderstorm code at 16:00: the 15:00 slot shows the worst code
    raw = {"hourly": {"time": [t.strftime("%Y-%m-%dT%H:%M") for t in times],
                      "apparent_temperature": [20.0 + i % 24 for i in range(72)], "precipitation": rain,
                      "snowfall": [0.0] * 72, "weather_code": codes, "is_day": [1] * 72}}
    slots = weather.hourly_slots(raw, dt.datetime(2026, 10, 21, 9, 40))
    assert len(slots) == 16 and slots[0]["time"] == dt.datetime(2026, 10, 21, 9), slots[0]
    assert all((b["time"] - a["time"]) == dt.timedelta(hours=3) for a, b in zip(slots, slots[1:]))
    s15 = next(s for s in slots if s["time"].hour == 15 and s["time"].day == 21)
    assert s15["weather_code"] == 95 and abs(s15["rain_mm"] - 1.5) < 1e-9 and s15["feels_like_c"] == 35.0, s15
    assert slots[0]["rain_mm"] == 0.0
    late = weather.hourly_slots(raw, dt.datetime(2026, 10, 23, 18))  # only 6 hours left in the forecast
    assert len(late) == 2
    assert weather.hourly_slots({}, dt.datetime(2026, 10, 21)) == []
    # "Worst" is the most dangerous code, not the highest number: freezing rain (66) beats rain showers (80).
    assert weather.worst_code([80, 66, 3]) == 66 and weather.worst_code([66, 95]) == 95
    assert weather.worst_code([71, 56]) == 56 and weather.worst_code([2, 48]) == 48
    print("ok: 48-hour strip (3-hour totals, worst weather code)")


def geocode_cases():
    """A replay's place ("Kolkata, India") still finds the place: search the name, keep the matching region."""
    asked = []
    results = [{"name": "Kolkata", "admin1": "West Bengal", "country": "India", "latitude": 22.56, "longitude": 88.36,
                "population": 4631392},
               {"name": "Kolkata", "admin1": "Somewhere", "country": "Elsewhere", "latitude": 1.0, "longitude": 2.0,
                "population": 9000000}]
    old = geocode._get
    geocode._get = lambda url, params: asked.append(params["name"]) or {"results": results}
    try:
        assert [p["label"] for p in geocode.search_places("Kolkata, India")] == ["Kolkata, West Bengal, India"]
        assert [p["label"] for p in geocode.search_places("Kolkata")][0] == "Kolkata, Somewhere, Elsewhere"  # most people
        assert len(geocode.search_places("Kolkata, Atlantis")) == 2  # nothing matches the rest: all results
    finally:
        geocode._get = old
    assert asked == ["Kolkata"] * 3, asked
    print("ok: place search with a region or country after a comma")


def main():
    cases = pd.read_csv(ROOT / "tests" / "cases.csv", dtype=str, keep_default_na=False)
    skipped = []
    with weather.offline():
        for _, c in cases.iterrows():
            if not c["date"]:
                skipped.append(c["name"])
                print("skipped (test day not picked yet):", c["name"])
                continue
            try:
                result = risk.assess(float(c["latitude"]), float(c["longitude"]), dt.date.fromisoformat(c["date"]))
            except weather.NotAvailable:
                skipped.append(c["name"])
                print("skipped (data not saved yet):", c["name"])
                continue
            special = replays.SPECIAL_NOTES.get(c["name"])
            check_result(c["name"], result, replays.place_of(c), special)
            if c["name"].startswith("Kolkata heat"):
                assert message.number_lines(result)[1] == (
                    "Feels-like high: 41 °C forecast, above the 40 °C danger line. About 48 days a year here, "
                    "1.4 times more often than in 1951–1980."), message.number_lines(result)[1]
                assert message.sms_text(result, "Kolkata, India") == (
                    "Groundtruth Kolkata, India 31 May 2022: High risk. Feels-like 41 C forecast. Avoid exertion, "
                    "drink water, check on older people. Check official warnings.")
            if c["name"].startswith("Texas"):  # the user's two examples
                numbers = message.number_lines(result)
                assert numbers[0] == ("Rain on 4 Jul 2025: 107 mm forecast. About once every 15 years here, about "
                                      "the same as in 1951–1980."), numbers[0]
                assert numbers[5] == ("Rain over 6 days: 144 mm (36.7 mm measured before the day, plus the day's "
                                      "forecast). About once every 4.3 years here, 3.5 times more often than in "
                                      "1951–1980."), numbers[5]
                assert message.level_line(result) == "107 mm of rain forecast in 24 h"
                assert message.headline(result) == "High risk of heavy rain."
                first, second = message.then_and_now(result)  # 24 h rain (2 + 2), then the 6-day rain (7 + 2)
                assert first["title"] == "Rain in 24 hours: 107 mm forecast", first["title"]
                assert second["title"] == "Rain over 6 days: 144 mm (36.7 mm measured plus the day's forecast)"
                assert [r["words"] for r in first["rows"]] == ["2 times in 30 years", "2 times in 30 years"]
                assert [r["words"] for r in second["rows"]] == ["7 times in 30 years", "2 times in 30 years"]
                assert second["rarer_now"] is None
            if c["name"] == "Paris snow and cold":  # no air temperature saved: the feels-like low (-6.5 °C) is used
                assert result.get("air_min_c") is None and message.ice_note(result) == message.ICE_NOTE
                assert message.ice_line(result) == "Roads may be icy; ice itself isn't checked."
                assert message.sms_text(result, "Paris, France") == (
                    "Groundtruth Paris, France 7 Jan 2026: Typical rain, temperature, snow and wind. Roads may be icy; "
                    "ice, storms, landslides not checked. Check official warnings.")
            if c["name"].startswith("Nepal-Tibet"):
                assert "glacier floods not checked" in message.sms_text(result, replays.place_of(c), special)
            if c["name"] in ("Bayesian sinking", "Nepal-Tibet glacier-collapse flood"):
                assert message.ice_note(result) is None and message.ice_line(result) is None
            if c["name"].startswith("Kolkata heat"):
                assert message.level_line(result) == ("Feels like 41 °C forecast, above the 40 °C danger line, "
                                                      "however often it happens here"), message.level_line(result)
                assert message.headline(result) == "High risk of dangerous feels-like heat."
                [block] = message.then_and_now(result)
                assert not block["counts"] and [r["words"] for r in block["rows"]] == ["about 48 times a year",
                                                                                       "about 34 times a year"]
                assert message.not_checked(result) == ("Not checked: thunderstorms, landslides, glacier collapse. "
                                                       "Follow official weather and storm warnings.")  # 34 °C low
                assert message.number_lines(result)[0] == "Rain on 31 May 2022: 8.2 mm forecast, normal for here."
            if c["name"] == "Valencia flash flood":
                assert message.level_line(result) == ("202 mm of rain forecast in 24 h, above the 150 mm danger "
                                                      "line; 257 mm of rain over 6 days"), message.level_line(result)
                assert message.headline(result) == "Extreme risk of heavy rain."  # the 24 h rain: first of the tie
                [block] = message.then_and_now(result)  # not seen in either period: the rows say so
                assert [r["words"] for r in block["rows"]] == ["not seen in those 30 years", "not seen in 1951–1980"]
            if c["name"] == "Paris snow and cold":  # ice first, then what the checks can't see; snow is rarer now
                assert message.summary_lines(result) == [  # the ice box, then "Not checked" without ice on roads
                    message.ICE_SMS, "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather "
                                     "and storm warnings."], message.summary_lines(result)
                [rarity] = message.then_and_now(result)
                assert rarity["name"] == "Snowfall (24 h)" and rarity["rarer_now"].startswith("Snow like this"), rarity
                numbers = message.number_lines(result)  # snow (1.1 a year) keeps its rate; cold (12 a year) is normal
                assert numbers[3] == ("Snow: 3.0 cm forecast. About 1.1 days a year here, down from about 1.3 days a "
                                      "year in 1951–1980."), numbers[3]
                assert numbers[2] == "Feels-like low: -6.5 °C forecast, normal for here.", numbers[2]
            if result["level"] == "Typical" and c["name"] != "Paris snow and cold":  # every check 5+ times a year
                assert message.then_and_now(result) == [], c["name"]
                warm = message._value(result, "feels_like_min_c") > message.ICE_MENTION_AT_OR_BELOW_C
                assert ("ice on roads" not in message.not_checked(result, special)) == warm, c["name"]
            if c["name"].startswith("Ordinary rain 1"):  # feels-like low 1.8 °C, no snow or rain on ice: ice listed
                assert "ice on roads" in message.not_checked(result), message.not_checked(result)
            if c["name"].startswith("Nepal-Tibet"):
                assert message.not_checked(result, special) == (
                    "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm "
                    "warnings. For glacier collapse and landslides, check civil protection and geological "
                    "authorities."), message.not_checked(result, special)
            print("ok:", c["name"], "->", result["level"])
    made_up_cases()
    hourly_cases()
    geocode_cases()
    check_result("Not enough data", not_enough_result())
    print("ok: Not enough data")
    # Every level/hazard combination, using made-up checks.
    for level in risk.LEVELS:
        for key in message.HAZARD_OF_CHECK:
            per = {"count": 3, "years": 30, "per_year": 0.1, "every_n_years": 10}
            check = {"key": key, "name": key, "unit": "mm", "value": 50.0, "level": level, "text": "t",
                     "baseline": per, "recent": per}
            r = {"level": level, "date": dt.date(2025, 1, 1), "checks": [check], "baseline_label": "1951–1980",
                 "recent_label": "1995–2024"}
            title = message.headline(r)
            if level == "Typical":
                assert title is None, title
            else:
                assert title == f"{level} risk of {message.HAZARD[key]}.", title
    print("ok: every level and hazard")
    print("All message checks passed." + (f" ({len(skipped)} saved-data cases skipped.)" if skipped else ""))


if __name__ == "__main__":
    main()
