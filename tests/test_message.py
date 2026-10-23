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
# "Normal" may only describe what a check measures (CLAUDE.md rule 8): "Normal rain for here" (the engine's text), or
# right after a check's value in "Other checks" / "All checks" ("Gusts up to 28 km/h, normal for here").
ALLOWED_NORMAL = re.compile(r"Normal (rain for here|rain for the last|temperatures for here|highs for here|"
                            r"lows for here|snowfall for here|wind for here)|normal for here$")


def check_text(label, result, texts):
    for t in texts:
        assert not FORBIDDEN.search(t), f"{label}: forbidden wording in: {t}"


def check_result(label, result, place="Somewhere, Far Away Land", special=None):
    today = dt.date.today()
    title = message.headline(result)
    normal = message.normal_lines(result)
    numbers = [f"{label} {value}" for _, label, value in normal] + message.not_enough_lines(result) \
        + message.data_notes(result)
    sms = message.sms_text(result, place, special)
    meaning = message.what_it_means(result, special)
    check_text(label, result, [title or "", sms, meaning, message.level_line(result), *numbers])
    for t in [meaning, *numbers]:
        for m in re.finditer(r"\bnormal\b", t, re.I):
            assert ALLOWED_NORMAL.match(t, m.start()), f"{label}: 'normal' used outside a check: {t}"
        # Less common than in the past must not sound reassuring.
        assert "less common" not in t, f"{label}: reassuring 'less common' wording: {t}"
    # "Normal for here": every check is either a card or a quiet line (or "not enough data"), never both.
    cards = message.then_and_now(result)
    carded = [card["key"] for card in cards]
    quiet = [key for key, _, _ in normal]
    assert not set(carded) & set(quiet), f"{label}: a check is both a card and a normal line"
    enough = [c["key"] for c in result["checks"] if c["level"] != risk.NOT_ENOUGH]
    assert sorted(carded + quiet) == sorted(enough), f"{label}: a check is missing: {carded} {quiet}"
    assert len(message.not_enough_lines(result)) == len(result["checks"]) - len(enough), label
    for key, name, value in normal:
        c = check(result, key)
        assert c["level"] not in risk.LEVELS[1:], f"{label}: a raised check among the normal lines"
        assert name == message.NORMAL_LABEL[key] and "**" not in value and "ERA5" not in value, (name, value)
        assert (c["recent"]["per_year"] < message.NORMAL_FROM_PER_YEAR) == (c["recent_text"] in value), value
        if value != "none forecast":  # "normal for here" exactly where the check happens 5+ times a year
            assert (c["recent"]["per_year"] >= message.NORMAL_FROM_PER_YEAR) == value.endswith(", normal for here")
    # The heading: "Other checks (n)" under cards, "All checks (n)" when there are none; n counts every line.
    n = len(normal) + len(message.not_enough_lines(result))
    assert message.checks_heading(result) == f"{'Other' if cards else 'All'} checks ({n})", label
    # The hero line: only on raised days (Typical and Not enough data have none, whatever the history).
    if result["level"] not in risk.LEVELS[1:]:
        assert message.hero_line(result, fake_history()) is None, f"{label}: a hero line on a {result['level']} day"

    # The yellow "Not checked" box is last on every result, and the page's one visible pointer to official warnings.
    lines = message.summary_lines(result, special)
    ice = message.ice_note(result)
    low = message._value(result, "feels_like_min_c")
    cold = low is None or low <= message.ICE_MENTION_AT_OR_BELOW_C
    box = message.NOT_CHECKED.format(ice=message.NOT_CHECKED_ICE if cold and not ice else "")
    if special == "geological":  # one sentence: official warnings and the geological authorities together
        box = box[:-1] + ", and civil protection and geological authorities."
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
        check_cards(label, result)
    else:
        assert message.headline(result) is None and "official sources" in message.level_line(result), label
        assert risk.NOT_ENOUGH_TEXT.replace("—", "-") in sms
        check_cards(label, result)


def check_cards(label, result):
    """"Then and now": one card per raised check, worst first; Typical days: only checks under 5 times a year."""
    cards = message.then_and_now(result)
    checks = [c for c in result["checks"] if "recent" in c]
    if result["level"] == "Typical":
        expect = [c for c in checks if c["recent"]["per_year"] < message.THEN_AND_NOW_TYPICAL_BELOW_PER_YEAR]
    else:
        expect = [c for c in checks if c["level"] in risk.LEVELS[1:]]
    assert sorted(id(c) for c in expect) == sorted(id(card["check"]) for card in cards), f"{label}: card checks"
    order = [(-risk.LEVELS.index(card["check"]["level"]), card["check"]["recent"]["per_year"]) for card in cards]
    assert order == sorted(order), f"{label}: cards not worst first"
    rows = [r for card in cards for r in card["rows"]]
    if rows:  # one shared scale: the most frequent row on the page is 1.0, the rest in proportion
        top = max(r["per_year"] for r in rows)
        assert sum(r["width"] == 1.0 for r in rows) >= 1, label
        for r in rows:
            assert abs(r["width"] - (r["per_year"] / top if top else 0.0)) < 1e-9, (label, r)
    for card in cards:
        c = card["check"]
        assert card["title"] == message.THEN_AND_NOW_TITLE[c["key"]], card["title"]
        assert card["chip"] == (None if c["level"] == "Typical" else c["level"]), f"{label}: chip {card['chip']}"
        assert card["value"] == message.amount(c["value"], c["unit"]), card["value"]
        if c["key"] == risk.RECENT_RAIN_KEY:  # part measured, part forecast: never just "forecast"
            assert card["value_note"] != "forecast" and "forecast" in card["value_note"], card["value_note"]
        else:
            assert card["value_note"].startswith("forecast"), card["value_note"]
        # The danger line is said once: in the level box for the checks it names, else on the card.
        named = c["name"] in (result.get("decided_by") or [])
        assert ("danger line" in card["value_note"]) == (bool(c.get("crosses_danger_line")) and not named), \
            f"{label}: {card['value_note']}"
        events = c["recent"]["count"] + c["baseline"]["count"]
        if not events:  # never seen in either period: no bars, the line names the check
            assert card["rows"] == [] and card["never"] == message.NEVER_SEEN.format(noun=message.NOUN[c["key"]])
            continue
        assert card["never"] is None, label
        assert [r["label"] for r in card["rows"]] == [f"Now ({result['recent_label']})", result["baseline_label"]]
        few = min(c["recent"]["count"], c["baseline"]["count"]) < message.ENOUGH_EVENTS
        assert card["counts"] == few, label
        for r, period, never in ((card["rows"][0], c["recent"], c["recent_text"]),
                                 (card["rows"][1], c["baseline"], c["baseline_text"])):
            if not period["count"]:  # "not seen in …" stays as the engine says it
                assert r["words"] == never, r
            elif few:  # few events: counts, not rates
                assert re.fullmatch(r"(once|\d+ times) in \d+ years", r["words"]), r
            else:
                assert r["words"] == never, r  # the engine's rate
        assert (card["rarer_now"] is not None) == (message.less_common_now(c) and events >= message.ENOUGH_EVENTS)
    # No sentence twice across the cards.
    said = [x for card in cards for x in (card["never"], card["rarer_now"]) if x]
    assert len(said) == len(set(said)), f"{label}: a card sentence twice: {said}"


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


# The hero line each replay gets (computed from the saved history; Typical replays get none).
REPLAY_HEROES = {
    "Valencia flash flood": "About 45% of a year's rain, forecast in one day",
    "Texas Hill Country flood": "About 16% of a year's rain, forecast in one day",
    # Kolkata: a feels-like high of 41.3 °C or more last happened the day before (30 May 2022): no hero line.
}


def check(result, key):
    return next(c for c in result["checks"] if c["key"] == key)


def made_up_cases():
    # Everything ordinary: the Typical headline, one merged temperature line, "No snow forecast".
    r, _ = fake_assess()
    check_result("made up: ordinary", r)
    normal = message.normal_lines(r)
    assert r["level"] == "Typical", r["level"]
    assert message.headline(r) is None  # Typical days have no headline
    assert message.level_line(r) == "for rain, temperature, snow and wind"
    assert message.ice_note(r) is None and message.ice_line(r) is None  # 1 mm of rain, above freezing
    assert normal[:5] == [("rain_mm", "Rain in 24 hours", "1.0 mm, normal for here"),
                          ("feels_like_max_c", "Feels-like high", "12 °C, normal for here"),
                          ("feels_like_min_c", "Feels-like low", "3.0 °C, normal for here"),
                          ("snow_cm", "Snow", "none forecast"),
                          ("gust_max_kmh", "Gusts", "up to 25 km/h, normal for here")], normal
    assert message.checks_heading(r) == "All checks (6)", message.checks_heading(r)
    assert normal[5][:2] == ("recent_rain_mm", "Rain over 6 days") and "measured" in normal[5][2], normal[5]
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
    assert "feels_like_min_c" not in [key for key, _, _ in message.normal_lines(r)], "a card, not a normal line"
    assert message.level_line(r).startswith("Feels as cold as "), message.level_line(r)
    rarity = message.then_and_now(r)[0]
    assert rarity["name"] == "Feels-like cold" and rarity["title"] == "Feels-like cold", rarity
    assert rarity["chip"] == r["level"] and rarity["value_note"] == "forecast", rarity
    first = rarity["rows"][0]["words"]
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
    assert ("snow_cm", "Snow", "2.0 cm, normal for here") in message.normal_lines(r), message.normal_lines(r)
    print("ok: made up: routine snow -> Typical")

    # Snow far beyond the record: Extreme, snow action line, snow "how often" caption.
    r, _ = fake_assess(snow_cm=30.0)
    check_result("made up: record snow", r)
    assert r["level"] == "Extreme" and message.summary_lines(r)[0] == message.ARROW + message.ACTIONS["snow"]
    assert message.headline(r) == "Extreme risk of heavy snow."
    [card] = message.then_and_now(r)
    assert (card["title"], card["value"], card["value_note"]) == ("Snow in 24 hours", "30 cm", "forecast"), card
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


def hero_cases():
    """The hero line from made-up history: share of a year (rain, 6-day rain, snow) or the last year (heat,
    cold, wind), the "more than a year" and "since 1951" cases, and none when the last such day was recent."""
    hist = fake_history()
    years = hist[(hist["date"].dt.year >= 1951) & (hist["date"].dt.year < FAKE_DATE.year)]
    rain_year = years.groupby(years["date"].dt.year)["rain_mm"].sum().mean()
    snow_year = years.groupby(years["date"].dt.year)["snow_cm"].sum().mean()

    def raised(key, value, level="High", **extra):
        c = {"key": key, "name": key, "unit": "", "value": value, "level": level, "notes": [],
             "lower_is_worse": key == "feels_like_min_c", "recent": {"count": 1, "per_year": 0.03},
             "baseline": {"count": 1, "per_year": 0.03}, **extra}
        return {"level": level, "date": FAKE_DATE, "checks": [c], "decided_by": [key]}

    # Rain, 6-day rain and snow: the share of an average year here, rounded to a whole percent.
    v = round(rain_year * 0.453, 1)
    assert message.hero_line(raised("rain_mm", v), hist) == \
        f"About {round(100 * v / rain_year)}% of a year's rain, forecast in one day"
    assert message.hero_line(raised("recent_rain_mm", v), hist) == \
        f"About {round(100 * v / rain_year)}% of a year's rain in 6 days, including the day's forecast"
    assert message.hero_line(raised("snow_cm", round(snow_year / 4, 1)), hist) == \
        f"About {round(100 * round(snow_year / 4, 1) / snow_year)}% of a year's snow, forecast in one day"
    # 100% or more, just under 100% (never shown as 100%).
    assert message.hero_line(raised("rain_mm", rain_year * 1.2), hist) == \
        "More than a year's rain, forecast in one day"
    assert message.hero_line(raised("rain_mm", rain_year * 0.996), hist) == \
        "About 99% of a year's rain, forecast in one day"
    # Under 10% of a year: no hero line (a small share could sound mild on a raised day); 10% exactly is shown.
    for share in (0.004, 0.04, 0.0999):
        assert message.hero_line(raised("rain_mm", rain_year * share), hist) is None, share
        assert message.hero_line(raised("snow_cm", snow_year * share), hist) is None, share
        assert message.hero_line(raised("recent_rain_mm", rain_year * share), hist) is None, share
    assert message.hero_line(raised("rain_mm", rain_year * 0.1), hist) == \
        "About 10% of a year's rain, forecast in one day"
    # An average year here has no snow at all: more than any day since the record began.
    dry = hist.assign(snow_cm=0.0)
    assert message.hero_line(raised("snow_cm", 5.0), dry) == "More snow than any day here since 1951"

    # Heat, cold, wind: the last year a day at least this extreme happened here.
    marked = hist.copy()
    when = marked["date"] == pd.Timestamp("2008-07-01")
    marked.loc[when, ["feels_like_max_c", "gust_max_kmh"]] = [60.0, 300.0]
    marked.loc[when, "feels_like_min_c"] = -60.0
    assert message.hero_line(raised("feels_like_max_c", 55.0), marked) == "The hottest feels-like day here since 2008"
    assert message.hero_line(raised("feels_like_min_c", -55.0), marked) == \
        "The coldest feels-like day here since 2008"  # checked in the cold direction
    assert message.hero_line(raised("gust_max_kmh", 250.0), marked) == "The strongest gusts here since 2008"
    # Never this extreme since the record began.
    assert message.hero_line(raised("feels_like_max_c", 70.0), marked) == "Hotter than any day here since 1951"
    assert message.hero_line(raised("feels_like_min_c", -70.0), marked) == "Colder than any day here since 1951"
    assert message.hero_line(raised("gust_max_kmh", 400.0), marked) == "Stronger gusts than any day here since 1951"
    # The last such day less than a year before the date: no hero line ("since 2024" on a 2024 date says nothing).
    recent = marked.copy()
    recent.loc[recent["date"] == pd.Timestamp("2024-06-01"), "feels_like_max_c"] = 60.0
    assert message.hero_line(raised("feels_like_max_c", 55.0), recent) is None
    # Typical, Not enough data and too little history: none.
    assert message.hero_line(raised("rain_mm", rain_year * 0.5, level="Typical"), hist) is None
    assert message.hero_line({**raised("rain_mm", 50.0), "level": risk.NOT_ENOUGH}, hist) is None
    short = hist[hist["date"].dt.year >= 2000]  # 24 full years: fewer than 30
    assert message.hero_line(raised("rain_mm", 50.0), short) is None
    assert message.hero_line(raised("rain_mm", 50.0), None) is None
    # Through the real engine: a record snow day gets a hero line; an ordinary day none.
    r, hist = fake_assess(snow_cm=30.0)
    assert message.hero_line(r, hist) == f"About {round(100 * 30 / snow_year)}% of a year's snow, forecast in one day"
    r, hist = fake_assess()
    assert message.hero_line(r, hist) is None
    print("ok: hero line (share of a year, last year, more than a year, since 1951, recent, Typical)")


def about_cases():
    """"About this tool": the user's wording, every number matching the risk.py settings."""
    assert message.HOW_LEVEL_SET == (
        "For each check (rain in 24 hours, rain over 6 days, heat, cold, snow and wind), we count how often a day at "
        "least this extreme happened at this spot in the last 30 years. Three danger lines (150 mm of rain in 24 "
        "hours, feels-like 40 °C, gusts of 100 km/h) mean at least High, however often they happen here. The page "
        "shows the worst level of all the checks. The 1951–1980 figures are only for comparison; they don't change "
        "the level."), message.HOW_LEVEL_SET
    assert message.LEVELS_MEAN == [
        "Typical: happens more than once a year here.",
        "Elevated: about once every 1 to 5 years.",
        "High: about once every 5 to 20 years, or past a danger line.",
        "Extreme: rarer than once every 20 years, or never seen here.",
        "Not enough data: we couldn't check reliably; follow official sources."], message.LEVELS_MEAN
    # The same numbers, straight from the settings.
    assert (risk.RECENT_WINDOW_YEARS, risk.RECENT_RAIN_DAYS_BEFORE + 1, risk.baseline_label()) == (30, 6, "1951–1980")
    assert risk.DANGER_LINES == {"rain_mm": 150, "feels_like_max_c": 40, "gust_max_kmh": 100}
    assert (risk.TYPICAL_IF_MORE_OFTEN_THAN_YEARS, risk.ELEVATED_IF_MORE_OFTEN_THAN_YEARS,
            risk.HIGH_IF_MORE_OFTEN_THAN_YEARS) == (1, 5, 20)
    assert risk.NOT_ENOUGH == "Not enough data"
    print("ok: About this tool (wording and numbers match risk.py)")


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
            history = weather.get_history(float(c["latitude"]), float(c["longitude"]),
                                          *message.hero_history_range(result["date"]))["data"]
            hero = message.hero_line(result, history)
            assert hero == REPLAY_HEROES.get(c["name"]), f"{c['name']}: hero line {hero}"
            if c["name"].startswith("Kolkata heat"):
                assert message.sms_text(result, "Kolkata, India") == (
                    "Groundtruth Kolkata, India 31 May 2022: High risk. Feels-like 41 C forecast. Avoid exertion, "
                    "drink water, check on older people. Check official warnings.")
            if c["name"].startswith("Texas"):  # the user's two examples
                assert message.level_line(result) == "107 mm of rain forecast in 24 h"
                assert message.headline(result) == "High risk of heavy rain."
                first, second = message.then_and_now(result)  # 24 h rain (High), then the 6-day rain (Elevated)
                assert (first["title"], first["chip"], first["value"], first["value_note"]) == (
                    "Rain in 24 hours", "High", "107 mm", "forecast"), first
                assert (second["title"], second["chip"], second["value"], second["value_note"]) == (
                    "Rain over 6 days", "Elevated", "144 mm", "36.7 mm measured + the day's forecast"), second
                assert [r["words"] for r in first["rows"]] == ["2 times in 30 years", "2 times in 30 years"]
                assert [r["words"] for r in second["rows"]] == ["7 times in 30 years", "2 times in 30 years"]
                assert second["rarer_now"] is None
                # One shared scale: "7 times" is the longest bar; every "2 times" bar is 2/7 of it, in both cards.
                assert second["rows"][0]["width"] == 1.0
                for r in (*first["rows"], second["rows"][1]):
                    assert abs(r["width"] - 2 / 7) < 0.01, r
                assert [key for key, _, _ in message.normal_lines(result)] == [
                    "feels_like_max_c", "feels_like_min_c", "snow_cm", "gust_max_kmh"]
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
                [block] = message.then_and_now(result)  # many such days: rates, not counts
                assert not block["counts"] and [r["words"] for r in block["rows"]] == ["about 48 times a year",
                                                                                       "about 34 times a year"]
                assert block["value_note"] == "forecast", block["value_note"]  # the level box names the 40 °C line
                assert message.not_checked(result) == ("Not checked: thunderstorms, landslides, glacier collapse. "
                                                       "Follow official weather and storm warnings.")  # 34 °C low
                assert message.normal_lines(result)[0] == ("rain_mm", "Rain in 24 hours", "8.2 mm, normal for here")
                assert message.checks_heading(result) == "Other checks (5)", message.checks_heading(result)
            if c["name"] == "Valencia flash flood":
                assert message.level_line(result) == ("202 mm of rain forecast in 24 h, above the 150 mm danger "
                                                      "line; 257 mm of rain over 6 days"), message.level_line(result)
                assert message.headline(result) == "Extreme risk of heavy rain."  # the 24 h rain: first of the tie
                first, second = message.then_and_now(result)  # neither seen in either period: no bars
                assert first["rows"] == [] == second["rows"]
                assert first["never"] == "Rain like this was never seen here in either period.", first["never"]
                assert second["never"] == "A wet spell like this was never seen here in either period."
                assert first["value_note"] == "forecast", first["value_note"]  # the level box names the 150 mm line
            if c["name"] == "Paris snow and cold":  # ice first, then what the checks can't see; snow is rarer now
                assert message.summary_lines(result) == [  # the ice box, then "Not checked" without ice on roads
                    message.ICE_SMS, "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather "
                                     "and storm warnings."], message.summary_lines(result)
                [rarity] = message.then_and_now(result)  # a Typical card: snow, about 1.1 times a year, no chip
                assert rarity["name"] == "Snowfall (24 h)" and rarity["rarer_now"].startswith("Snow like this"), rarity
                assert rarity["chip"] is None and [r["words"] for r in rarity["rows"]] == [
                    "about 1.1 times a year", "about 1.3 times a year"], rarity
                normal = message.normal_lines(result)  # snow is a card; cold (12 a year) is a normal line
                assert "snow_cm" not in [key for key, _, _ in normal], normal
                assert ("feels_like_min_c", "Feels-like low", "-6.5 °C, normal for here") in normal, normal
                assert message.checks_heading(result) == "Other checks (5)", message.checks_heading(result)
            if result["level"] == "Typical" and c["name"] != "Paris snow and cold":  # every check 5+ times a year
                assert message.then_and_now(result) == [], c["name"]
                warm = message._value(result, "feels_like_min_c") > message.ICE_MENTION_AT_OR_BELOW_C
                assert ("ice on roads" not in message.not_checked(result, special)) == warm, c["name"]
            if c["name"].startswith("Ordinary rain 1"):  # feels-like low 1.8 °C, no snow or rain on ice: ice listed
                assert "ice on roads" in message.not_checked(result), message.not_checked(result)
            if c["name"].startswith("Nepal-Tibet"):
                assert message.not_checked(result, special) == (
                    "Not checked: thunderstorms, landslides, glacier collapse. Follow official weather and storm "
                    "warnings, and civil protection and geological authorities."), message.not_checked(result, special)
            print("ok:", c["name"], "->", result["level"])
    made_up_cases()
    hero_cases()
    about_cases()
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
