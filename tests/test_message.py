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

from groundtruth import message, replays, risk, weather  # noqa: E402

FORBIDDEN = re.compile(r"\bsafe\b|\bsafely\b|\bsafety\b|\bno risk\b|\ball clear\b|\bcaused\b", re.I)
# "Normal" may only describe what a check measures (CLAUDE.md rule 8).
ALLOWED_NORMAL = re.compile(r"Normal (rain for here|rain for the last|temperatures for here|highs for here|"
                            r"lows for here|snowfall for here|wind for here)")


def check_text(label, result, texts):
    for t in texts:
        assert not FORBIDDEN.search(t), f"{label}: forbidden wording in: {t}"


def check_result(label, result, place="Somewhere, Far Away Land", special=None):
    today = dt.date.today()
    sentence = message.template_sentence(result, today)
    bullets = message.why_bullets(result)
    sms = message.sms_text(result, place, special)
    meaning = message.what_it_means(result, special)
    check_text(label, result, [sentence, sms, meaning, *bullets])
    for t in [sentence, *bullets]:
        for m in re.finditer(r"\bnormal\b", t, re.I):
            assert ALLOWED_NORMAL.match(t, m.start()), f"{label}: 'normal' used outside a check: {t}"
        # Less common than in the past must not sound reassuring.
        assert "less common" not in t, f"{label}: reassuring 'less common' wording: {t}"
    # "Normal temperatures" only when both temperature checks are Typical.
    levels = {c["key"]: c["level"] for c in result["checks"]}
    both = levels.get("feels_like_max_c") == levels.get("feels_like_min_c") == "Typical"
    assert any("Normal temperatures" in b for b in bullets) == both, f"{label}: temperature line rule"

    # The yellow STORM_LINE is the page's one visible pointer to official warnings, last on every result.
    lines = message.summary_lines(result, special)
    assert lines[-1] == message.STORM_LINE, f"{label}: {lines}"
    assert " ".join(lines).lower().count("official") == 1, f"{label}: official warnings said more than once: {lines}"
    assert message.OFFICIAL_LINE not in sentence and message.OFFICIAL_LINE not in " ".join(lines), label
    assert "official" in sms.lower(), f"{label}: SMS must point to official warnings"
    assert len(sms) <= 160, f"{label}: SMS is {len(sms)} characters"
    assert sms.isascii(), f"{label}: SMS should be plain ASCII"
    assert len(message.sms_text(result, "A" * 300, special)) <= 160, f"{label}: SMS too long with a long place name"
    # A Typical SMS says what is typical, never "Typical weather" (also with a very long place name).
    # It always says what isn't checked; any other level always carries its short action. Neither is dropped.
    ice = message.ice_note(result)
    typical = result["level"] == "Typical"
    for s in (sms, message.sms_text(result, "A" * 300, special)):
        assert "Typical weather" not in s and "Typical risk" not in s, f"{label}: {s}"
        assert ("Typical rain, temperature, snow and wind" in s) == typical, f"{label}: {s}"
        # Always the sender and the date, so a forwarded message can't read as today's.
        assert s.startswith("Groundtruth ") and message._ascii(message.day_text(result["date"])) in s, f"{label}: {s}"
        if typical:  # what isn't checked, said once: storms, ice and landslides (+ glacier floods for the note)
            low = s.lower()
            assert all(re.search(rf"\b{w}\b", low) for w in ("storms", "ice", "landslides", "not checked")), s
            assert ("glacier floods not checked" in s) == (special == "geological"), f"{label}: {s}"
            assert len(re.findall(r"\bice\b", low)) == 1 and "Roads may be icy." not in s, f"{label}: ice twice: {s}"
        else:
            assert "landslides" not in s, f"{label}: {s}"
        if result["level"] in risk.LEVELS[1:] and message.sms_action(result):
            assert message.sms_action(result) in s, f"{label}: short action dropped: {s}"
        assert ("Roads may be icy" in s) == bool(ice), f"{label}: ice note in the SMS: {s}"
    # The lines under the level box, written by code. Typical: the ice note (if any), then what the checks
    # can't see. Raised: the action line with an arrow, then the ice line. Then the geological note.
    assert meaning == " ".join(lines)
    if result["level"] in risk.LEVELS:
        if typical:
            expect = [message.ICE_TYPICAL] if ice else []
            expect.append(message.TYPICAL_LIMITS)
            assert len(re.findall(r"\bice\b", " ".join(lines).lower())) == 1, f"{label}: ice twice: {lines}"
        else:
            expect = [message.ARROW + message.action_line(result)] if message.action_line(result) else []
            expect += [message.ICE_SMS] if ice else []
        expect += [message.GEOLOGICAL_NOTE] if special == "geological" else []
        assert lines == expect + [message.STORM_LINE], f"{label}: {lines}"
        assert not re.search(r"\d", meaning), f"{label}: a number in the lines under the level box: {meaning}"
        if typical:
            assert message.level_line(result) == message.TYPICAL_LEVEL_LINE, label
        else:
            assert message.level_line(result).startswith("Set by "), label
            for c in result["checks"]:
                if c["name"] in result["decided_by"] and c.get("crosses_danger_line"):
                    assert f"{c['danger_line']} {c['unit']} danger line" in message.level_line(result), label
    else:
        assert lines == [message.STORM_LINE] and "official sources" in message.level_line(result), label
    # The ice note goes in the sentence when it applies; the day's figures are always labelled a forecast.
    assert (message.ICE_NOTE in sentence) == bool(ice), f"{label}: ice note in the sentence"
    assert "Normal conditions" not in sentence, f"{label}: whole-day verdict: {sentence}"
    assert bullets[-1] == f"**About these figures:** {message.FORECAST_NOTE}", f"{label}: {bullets[-1]}"
    for b in bullets:
        assert "Normal wind for here" not in b or "misses sudden local storm gusts" in b, f"{label}: {b}"
        assert not ("danger line" in b and "common here" in b), f"{label}: danger line day called common: {b}"

    if result["level"] in risk.LEVELS:
        # The headline always matches the computed level (and no other level's headline appears).
        assert_headline(label, sentence, result["level"], today)
        assert re.search(rf"\b{result['level']}\b", sms), f"{label}: SMS level word does not match"
        # No numbers at all in the sentence (so it can't add one that isn't in the facts).
        assert not re.search(r"\d", sentence), f"{label}: sentence contains a number"
        # Action line: none for Typical, otherwise exactly one of the fixed lines.
        actions = [a for a in message.ACTIONS.values() if a in sentence]
        assert len(actions) == (0 if result["level"] == "Typical" else 1), f"{label}: action lines {actions}"
        # "Then and now" on every level: now first, then the comparison period.
        rarity = message.rarity_rows(result)
        assert rarity is not None, f"{label}: then and now missing"
        assert [r["label"] for r in rarity["rows"]] == [f"Now ({result['recent_label']})", result["baseline_label"]]
        assert max(r["width"] for r in rarity["rows"]) in (0.0, 1.0)
        assert (rarity["rarer_now"] is not None) == message.less_common_now(message.deciding_check(result)), label
        # What decided the level comes first in the Why list.
        first = bullets[0]
        assert result["level"] == "Typical" or first.startswith("**") and "Normal" not in first, f"{label}: {first}"
        assert "ERA5" not in " ".join(bullets), f"{label}: source text belongs in Details"
        assert "Level:" not in sentence and "See the reasons" not in sentence
    else:
        assert risk.NOT_ENOUGH_TEXT in sentence and risk.NOT_ENOUGH_TEXT.replace("—", "-") in sms
        assert message.rarity_rows(result) is None


def assert_headline(label, sentence, level, today):
    for other, text in message.HEADLINES.items():
        said = any(sentence.startswith(text.format(when=w)) for w in ("today", "on this day"))
        assert said == (other == level), f"{label}: headline for {other} {'missing' if other == level else 'present'}"


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
    bullets = message.why_bullets(r)
    assert r["level"] == "Typical", r["level"]
    assert message.template_sentence(r) == (
        "Typical rain, temperature, snow and wind for here. These checks can't see thunderstorms, ice on roads, or "
        "landslides and glacier collapse."), message.template_sentence(r)
    assert message.level_line(r) == "for rain, temperature, snow and wind"
    assert message.ice_note(r) is None and message.ice_line(r) is None  # 1 mm of rain, above freezing
    assert "**Temperature:** Normal temperatures for here (feels like 3 to 12 °C)" in bullets, bullets
    assert "**Snowfall (24 h):** No snow forecast" in bullets, bullets
    assert any(b.startswith("**Recent rain (6-day total):** Normal rain for the last 6 days") for b in bullets), bullets
    print("ok: made up: ordinary day -> Typical")

    # A rare cold day: raises the level, cold action line, and "less common now" isn't reassuring.
    _, hist = fake_assess()
    recent = hist[hist["date"].dt.year >= 1994]["feels_like_min_c"].sort_values()
    r, _ = fake_assess(feels_like_min_c=float(recent.iloc[3]))  # about 4 days this cold in 30 years
    check_result("made up: rare cold", r)
    cold = check(r, "feels_like_min_c")
    assert r["level"] in ("Elevated", "High", "Extreme") and cold["level"] == r["level"], (r["level"], cold["level"])
    assert cold["ratio"] is not None and cold["ratio"] < 1, cold["ratio_text"]
    assert message.ACTIONS["cold"] in message.template_sentence(r)
    first = message.why_bullets(r)[0]
    assert first.startswith("**Forecast to feel as cold as") and "It was more frequent in 1951–1980" in first, first
    assert "doesn't make today any less serious" in first, first
    assert "**Feels-like heat:** Normal highs for here" in " ".join(message.why_bullets(r))
    rarity = message.rarity_rows(r)
    assert rarity["name"] == "Feels-like cold" and rarity["like_this"] == "days at least this cold"
    assert rarity["rarer_now"] == ("Cold like this is rarer here now, so people and places may be less prepared "
                                   "for it."), rarity
    print(f"ok: made up: rare cold -> {r['level']}\n    {first}")

    # Heat over the danger line with ordinary cold: two lines, never "normal temperatures".
    r, _ = fake_assess(feels_like_max_c=41.0)
    check_result("made up: heat", r)
    assert r["level"] in ("High", "Extreme")
    assert any("Normal lows for here" in b for b in message.why_bullets(r))
    print(f"ok: made up: heat -> {r['level']}")

    # Routine snow: Typical, with the snowfall wording.
    r, _ = fake_assess(snow_cm=2.0)
    check_result("made up: routine snow", r)
    assert check(r, "snow_cm")["level"] == "Typical" and r["level"] == "Typical", check(r, "snow_cm")
    assert "**Snowfall (24 h):** Normal snowfall for here (2.0 cm)" in message.why_bullets(r)
    print("ok: made up: routine snow -> Typical")

    # Snow far beyond the record: Extreme, snow action line, snow "how often" caption.
    r, _ = fake_assess(snow_cm=30.0)
    check_result("made up: record snow", r)
    assert r["level"] == "Extreme" and message.ACTIONS["snow"] in message.template_sentence(r)
    assert message.rarity_rows(r)["like_this"] == "days with at least this much snow"
    print("ok: made up: record snow -> Extreme")

    # The ice note uses the lower of the day's lowest air temperature and its feels-like low, at +1 °C or below.
    r, _ = fake_assess(snow_cm=2.0, feels_like_max_c=2.0, air_min_c=-5.0)  # +2 °C by day, -5 °C overnight, snow
    check_result("made up: snow, +2 by day, -5 overnight", r)
    assert message.ice_note(r) == message.ICE_NOTE, "a day that drops to -5 °C with snow must get the ice note"
    assert message.ICE_NOTE in message.template_sentence(r) and "Roads may be icy" in message.sms_text(r, "Somewhere")
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

    # A danger-line day that was more frequent in 1951–1980: the danger line sets the level.
    c = {"key": "feels_like_max_c", "name": "Feels-like heat", "unit": "°C", "value": 41.0, "danger_line": 40,
         "crosses_danger_line": True, "relative_level": "Typical", "level": "High", "ratio": 0.8,
         "recent": {"count": 600, "per_year": 20.0}, "recent_text": "about 20 times a year",
         "baseline_text": "about 25 times a year", "ratio_text": "1.2 times less common here than in 1951–1980"}
    bullet = message._unusual_bullet(c, {"baseline_label": "1951–1980"})
    assert bullet.endswith("the danger line sets the level.") and "less common" not in bullet, bullet
    print("ok: danger-line bullet when it was more frequent before")

    # The scope line names what we don't check.
    for word in ("thunderstorms", "hail", "freezing rain", "wildfire", "air quality", "coastal flooding",
                 "geological"):
        assert word in message.SCOPE_LINE, word
    for word in ("thunderstorms", "hail", "freezing rain", "wildfire", "air quality", "coastal flooding",
                 "civil protection", "geological authorities"):
        assert word in message.NOT_CHECKED_LINE, word
    assert "Thunderstorms are not checked" in message.STORM_NOTE
    assert message.STORM_LINE == "Thunderstorms aren't checked. Follow official weather and storm warnings."
    assert message.OFFICIAL_LINE == "Check your official weather warnings. Groundtruth never replaces them."
    print("ok: scope line, storm note and the yellow storm line")


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
                assert message.why_bullets(result)[0] == (
                    "**Forecast to feel like 41 °C** — above the 40 °C danger line. That line matters however often "
                    "this happens here: about 48 days a year, 1.4 times more common than in 1951–1980."), \
                    message.why_bullets(result)[0]
                assert message.sms_text(result, "Kolkata, India") == (
                    "Groundtruth Kolkata, India 31 May 2022: High risk. Feels-like 41 C forecast. Avoid exertion, "
                    "drink water, check on older people. Check official warnings.")
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
                assert message.level_line(result) == "Set by Feels-like heat, above the 40 °C danger line"
                assert message.rarity_rows(result)["danger_note"] == message.DANGER_LINE_NOTE
            if c["name"] == "Valencia flash flood":
                assert message.level_line(result) == ("Set by Rain (24 h), above the 150 mm danger line, and "
                                                      "Recent rain (6-day total)"), message.level_line(result)
            if c["name"] == "Paris snow and cold":  # ice first, then what the checks can't see; snow is rarer now
                assert message.summary_lines(result)[:2] == [message.ICE_TYPICAL, message.TYPICAL_LIMITS]
                rarity = message.rarity_rows(result)
                assert rarity["name"] == "Snowfall (24 h)" and rarity["rarer_now"].startswith("Snow like this"), rarity
            if c["name"].startswith("Nepal-Tibet"):
                assert message.GEOLOGICAL_NOTE in message.summary_lines(result, special)
            print("ok:", c["name"], "->", result["level"])
    made_up_cases()
    hourly_cases()
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
            sentence = message.template_sentence(r, dt.date(2025, 1, 1))
            assert_headline("synthetic", sentence, level, dt.date(2025, 1, 1))
    print("ok: every level and hazard")
    print("All message checks passed." + (f" ({len(skipped)} saved-data cases skipped.)" if skipped else ""))


if __name__ == "__main__":
    main()
