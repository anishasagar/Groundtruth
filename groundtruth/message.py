"""Plain-language text built from the risk engine's numbers (no language model).

Nothing here decides a level or invents a number: it only puts what `risk.assess`
returned into words. Never uses the words "safe", "no risk" or "all clear", and
never says climate change caused anything.
"""

import datetime as dt
import unicodedata

import pandas as pd

from groundtruth import risk

# The first line of "How sure are we". The visible pointer to official warnings is the "Not checked" box.
OFFICIAL_LINE = risk.ALWAYS_NOTES[0]
# The one yellow "Not checked" box on every result: what the checks can't see, and the page's visible pointer
# to official warnings. "ice on roads, " is left out when the ice box shows or the feels-like low is above 5 °C.
NOT_CHECKED = "Not checked: thunderstorms, {ice}landslides, glacier collapse. Follow official weather and storm warnings."
NOT_CHECKED_ICE = "ice on roads, "
# The Nepal-Tibet replay (glacier collapse): the box's last sentence ends with this instead of ".".
NOT_CHECKED_GEOLOGICAL_END = ", and civil protection and geological authorities."

# The line under the level word on a Typical day: what is typical (never "Typical weather").
TYPICAL_LEVEL_LINE = "for rain, temperature, snow and wind"
# "How sure are we": exactly these four lines.
HOW_SURE_LINES = [
    OFFICIAL_LINE,
    "The history data is a grid of about 25 km, so it misses very local storms.",
    "Forecasts can be too low.",
    "Weather only: for landslides, glacier collapse and earthquakes, check local civil protection and geological "
    "authorities.",
]
# "About this tool" (cold and snow have no danger line, so they can only be raised by how rare they are here).
NO_COLD_SNOW_LINES = ("There are no fixed danger lines for cold or snow yet; fixed cold lines need research. "
                      "Those two checks use only how rare the day is here.")
# "About this tool": how the level is set and what the levels mean (every number from the risk.py settings).
_DAYS = risk.RECENT_RAIN_DAYS_BEFORE + 1
_LINES = risk.DANGER_LINES
HOW_LEVEL_SET = (
    f"For each check (rain in 24 hours, rain over {_DAYS} days, heat, cold, snow and wind), we count how often a "
    f"day at least this extreme happened at this spot in the last {risk.RECENT_WINDOW_YEARS} years. "
    f"Three danger lines ({_LINES['rain_mm']} mm of rain in 24 hours, feels-like {_LINES['feels_like_max_c']} °C, "
    f"gusts of {_LINES['gust_max_kmh']} km/h) mean at least High, however often they happen here. "
    "The page shows the worst level of all the checks. "
    f"The {risk.baseline_label()} figures are only for comparison; they don't change the level."
)


def _once_every(years):
    return "once a year" if years == 1 else f"once every {years} years"


LEVELS_MEAN = [
    f"Typical: happens more than {_once_every(risk.TYPICAL_IF_MORE_OFTEN_THAN_YEARS)} here.",
    f"Elevated: about once every {risk.TYPICAL_IF_MORE_OFTEN_THAN_YEARS} to "
    f"{risk.ELEVATED_IF_MORE_OFTEN_THAN_YEARS} years.",
    f"High: about once every {risk.ELEVATED_IF_MORE_OFTEN_THAN_YEARS} to {risk.HIGH_IF_MORE_OFTEN_THAN_YEARS} "
    "years, or past a danger line.",
    f"Extreme: rarer than {_once_every(risk.HIGH_IF_MORE_OFTEN_THAN_YEARS)}, or never seen here.",
    f"{risk.NOT_ENOUGH}: we couldn't check reliably; follow official sources.",
]
# "Then and now", when the check is less common now than in the comparison period.
RARER_NOW = "{noun} like this is rarer here now, so people and places may be less prepared for it."
# "Then and now", when the check wasn't seen in either period (no bars). Names the check, so never said twice.
NEVER_SEEN = "{noun} like this was never seen here in either period."
# On Typical days "Then and now" is shown only for a check that happens fewer than this many times a year now
# (Paris snow, about 1.1: yes; a few tenths of a mm of rain, about 45: no, the section is hidden).
THEN_AND_NOW_TYPICAL_BELOW_PER_YEAR = 5
# Fewer than this many such days (or wet spells) in either period: the rows give counts ("7 times in 30 years"),
# not rates. Fewer in both periods together: the next raised check is shown too, and no "rarer here now".
ENOUGH_EVENTS = 5
# Under the "Then and now" heading.
THEN_AND_NOW_CAPTION = "How often days like this happen here."
# Added to the level box when a danger line, not how rare the day is here, set the level.
HOWEVER_OFTEN = ", however often it happens here"
# "Normal for here": a check that happens fewer than this many times a year now keeps its rate after the value.
NORMAL_FROM_PER_YEAR = 5
NORMAL_SMALL_PRINT = "All values are forecasts unless marked measured."
# Streamlit's built-in Material icons, one per check.
ICONS = {"rain_mm": ":material/rainy:", "recent_rain_mm": ":material/water_drop:",
         "feels_like_max_c": ":material/thermostat:", "feels_like_min_c": ":material/severe_cold:",
         "snow_cm": ":material/weather_snowy:", "gust_max_kmh": ":material/air:"}

# The hero line in the level box on raised days, from the check that set the level and the history at that spot.
# Rain and snow: the value as a share of an average year's total. "{noun}" is rain or snow.
HERO_SHARE = {"rain_mm": ("rain", ", forecast in one day"),
              "recent_rain_mm": ("rain", f" in {risk.RECENT_RAIN_DAYS_BEFORE + 1} days, including the day's forecast"),
              "snow_cm": ("snow", ", forecast in one day")}
HERO_SHARE_COLUMN = {"rain_mm": "rain_mm", "recent_rain_mm": "rain_mm", "snow_cm": "snow_cm"}
# Heat, cold and wind: the last year a day at least this extreme happened here, or none since the record began.
HERO_SINCE = {"feels_like_max_c": ("The hottest feels-like day here since {year}", "Hotter than any day here since {year}"),
              "feels_like_min_c": ("The coldest feels-like day here since {year}", "Colder than any day here since {year}"),
              "gust_max_kmh": ("The strongest gusts here since {year}", "Stronger gusts than any day here since {year}")}
# No hero line when the last such day was this recent ("the hottest since 2022" on a 2022 date says nothing).
HERO_RECENT_DAYS = 365
# The share-of-a-year line is shown only at this share or more: a small share ("About 4% of a year's rain") could
# sound mild in the boldest line of a raised level box. Below it, no hero line.
HERO_MIN_SHARE_PERCENT = 10
# The "Not checked" box mentions ice on roads only when the day's feels-like low is at or below this.
ICE_MENTION_AT_OR_BELOW_C = 5
ARROW = "→ "

# Part of the facts sent to Claude (and so of each saved reply's fingerprint; Claude is off, kept for Phase 2).
# Not shown on the page.
SCOPE_LINE = ("We check rain, heat, cold, snow, wind and recent rain. We don't yet check thunderstorms, "
              "hail, freezing rain or ice, wildfire, air quality, coastal flooding, or geological hazards. "
              "For those, follow official warnings.")
STORM_NOTE = ("**Thunderstorms are not checked.** Storms are a major cause of weather deaths — "
              "follow official storm warnings.")
GEOLOGICAL_NOTE = ("Groundtruth covers weather-driven hazards only. For geological hazards (landslides, "
                   "glacier collapse, earthquakes), check local civil protection and geological authorities.")

# The headline on raised days, written by code: "<Level> risk of <hazard>." (Typical days have none.)
HAZARD = {"rain_mm": "heavy rain", "recent_rain_mm": "heavy rain over several days",
          "feels_like_max_c": "extreme feels-like heat", "feels_like_min_c": "extreme cold", "snow_cm": "heavy snow",
          "gust_max_kmh": "strong wind"}
HAZARD_DANGER_LINE = {"feels_like_max_c": "dangerous feels-like heat"}  # when its danger line was crossed

# One fixed action line per hazard. None for Typical.
ACTIONS = {
    "rain": "Avoid underpasses, low roads and riverbanks.",
    "heat": "Avoid heavy exertion outdoors, drink water, and check on older or vulnerable people.",
    "wind": "Secure loose objects and stay away from trees.",
    "snow": "Avoid unnecessary travel; roads and transport may be disrupted.",
    "cold": "Dress in layers, limit time outside, and check on older or vulnerable people.",
}
# The same actions, short enough for a text message. Never dropped from one.
SMS_ACTIONS = {
    "rain": "Avoid low roads and riverbanks.",
    "heat": "Avoid exertion, drink water, check on older people.",
    "wind": "Secure loose objects, stay away from trees.",
    "snow": "Avoid unnecessary travel.",
    "cold": "Dress warmly, check on older people.",
}
HAZARD_OF_CHECK = {"rain_mm": "rain", "recent_rain_mm": "rain", "feels_like_max_c": "heat",
                   "feels_like_min_c": "cold", "snow_cm": "snow", "gust_max_kmh": "wind"}

SHORT_NAMES = {"rain_mm": "Rain", "recent_rain_mm": "6-day rain", "feels_like_max_c": "Feels-like",
               "feels_like_min_c": "Feels-like low", "snow_cm": "Snow", "gust_max_kmh": "Gusts"}

SMS_LIMIT = 160
# What a Typical level covers. "Typical weather" would sound like everything is fine.
TYPICAL_SCOPE = "Typical rain, temperature, snow and wind"
# Every Typical text message ends with what isn't checked (never dropped to save space).
TYPICAL_SMS_LIMITS = "Storms, ice, landslides not checked."
TYPICAL_SMS_LIMITS_GEOLOGICAL = "Storms, ice, landslides, glacier floods not checked."

# Snow or rain on a day that drops to about freezing. Ice itself isn't checked yet (Phase 2).
ICE_NOTE = "Snow or rain on freezing ground can make roads icy, and ice isn't checked."
ICE_SMS = "Roads may be icy; ice itself isn't checked."  # also the yellow ice box on the page
ICE_SMS_TYPICAL = "Roads may be icy; "  # + the not-checked list, starting with ice (one sentence, so it fits)
ICE_IF_AT_OR_BELOW_C = 1.0  # a margin: black ice forms with air just above 0 °C over frozen ground

# The day's values come from a forecast, also for past days (the past-forecast archive).
FORECAST_NOTE = "The day's figures are a forecast and can be too low."
# Sent to Claude (facts; kept for Phase 2). On the page the level box says "however often it happens here".
DANGER_LINE_NOTE = "This is at or above the danger line, so it matters however often it happens here."


def day_text(date):
    return f"{date.day} {date:%b %Y}"


def amount(value, unit):
    return f"{value:.1f} {unit}" if abs(value) < 10 else f"{value:.0f} {unit}"


def deciding_check(result):
    """The check that sets the level. If several tie, the rarest one in the recent window."""
    if result["level"] not in risk.LEVELS:
        return None
    tied = [c for c in result["checks"] if c["level"] == result["level"] and "recent" in c]
    if not tied:
        return None
    return min(tied, key=lambda c: c["recent"]["per_year"])  # min keeps the first on a tie


def action_line(result, actions=ACTIONS):
    if result["level"] == "Typical":
        return None
    check = deciding_check(result)
    return actions.get(HAZARD_OF_CHECK.get(check["key"])) if check else None


def sms_action(result):
    return action_line(result, SMS_ACTIONS)


def _value(result, key):
    c = next((c for c in result["checks"] if c["key"] == key), None)
    v = None if c is None else c.get("value")
    return None if v is None or pd.isna(v) else v


def ice_note(result):
    """ICE_NOTE when snow or rain is forecast and the day drops to +1 °C or below, else None.

    Uses the lower of the day's lowest air temperature and its feels-like low (whichever exist).
    """
    wet = any((_value(result, k) or 0) > 0 for k in ("rain_mm", "snow_cm"))
    air = result.get("air_min_c")
    lows = [v for v in (None if air is None or pd.isna(air) else air, _value(result, "feels_like_min_c"))
            if v is not None]
    return ICE_NOTE if wet and lows and min(lows) <= ICE_IF_AT_OR_BELOW_C else None


def ice_line(result):
    """The line shown on its own right under the headline when the ice note applies, else None."""
    return ICE_SMS if ice_note(result) else None


def danger_line_set_level(c):
    """True when the danger line, not how rare the value is here, set this check's level."""
    return bool(c.get("crosses_danger_line")) and c.get("relative_level") in risk.LEVELS \
        and risk.LEVELS.index(c["relative_level"]) < risk.LEVELS.index(c["level"])


def level_line(result):
    """The one line under the level word: what Typical covers, or what set a raised level."""
    level = result["level"]
    if level not in risk.LEVELS:
        return "Check official sources."
    if level == "Typical":
        return TYPICAL_LEVEL_LINE
    by_name = {c["name"]: c for c in result["checks"]}
    parts = []  # "Feels like 41 °C forecast, above the 40 °C danger line, however often it happens here"
    for name in result.get("decided_by") or []:
        c = by_name[name]
        parts.append(LEVEL_VALUE[c["key"]].format(v=amount(c["value"], c["unit"])) + _danger_text(c)
                     + (HOWEVER_OFTEN if danger_line_set_level(c) else ""))
    return "; ".join(parts)


def headline(result):
    """"High risk of dangerous feels-like heat." on raised days, from the check that set the level; else None."""
    if result["level"] not in risk.LEVELS[1:]:
        return None
    c = deciding_check(result)
    hazard = HAZARD_DANGER_LINE.get(c["key"]) if c.get("crosses_danger_line") else None
    return f"{result['level']} risk of {hazard or HAZARD[c['key']]}."


def not_checked(result, special=None):
    """The yellow "Not checked" box: on every result, with "ice on roads" only on a cold day without the ice box."""
    low = _value(result, "feels_like_min_c")
    cold = low is None or low <= ICE_MENTION_AT_OR_BELOW_C  # a missing low counts as cold: over-warn
    text = NOT_CHECKED.format(ice=NOT_CHECKED_ICE if cold and not ice_note(result) else "")
    return text[:-1] + NOT_CHECKED_GEOLOGICAL_END if special == "geological" else text


def _danger_text(c):
    """", above the 40 °C danger line" when the check crossed its line, else ""."""
    if not c.get("crosses_danger_line"):
        return ""
    how = "above" if c["value"] > c["danger_line"] else "at"
    return f", {how} the {c['danger_line']} {c['unit']} danger line"


def summary_lines(result, special=None):
    """The code-written lines under the headline, in screen order: the action line (raised days), the ice box
    (yellow, when it applies), and last the yellow "Not checked" box (every result).
    special: "storm" or "geological" (replays.SPECIAL_NOTES).
    """
    action = action_line(result) if result["level"] in risk.LEVELS else None
    lines = [ARROW + action if action else None, ICE_SMS if ice_note(result) else None]
    return [line for line in lines if line] + [not_checked(result, special)]


def what_it_means(result, special=None):
    """The headline and the lines under it as one text, for the test log."""
    return " ".join(p for p in (headline(result), *summary_lines(result, special)) if p)


# The level box line on raised days: the value that set the level.
LEVEL_VALUE = {
    "rain_mm": "{v} of rain forecast in 24 h",
    "recent_rain_mm": "{v} of rain over 6 days",
    "feels_like_max_c": "Feels like {v} forecast",
    "feels_like_min_c": "Feels as cold as {v} forecast",
    "snow_cm": "{v} of snow forecast in 24 h",
    "gust_max_kmh": "Gusts up to {v} forecast",
}
# What "like this" refers to ("Snow like this is rarer here now…").
NOUN = {"rain_mm": "Rain", "recent_rain_mm": "A wet spell", "feels_like_max_c": "Heat", "feels_like_min_c": "Cold",
        "snow_cm": "Snow", "gust_max_kmh": "Wind"}
# "Normal for here": one quiet line per check, label and value.
NORMAL_LABEL = {"rain_mm": "Rain in 24 hours", "recent_rain_mm": "Rain over 6 days", "feels_like_max_c": "Feels-like high",
                "feels_like_min_c": "Feels-like low", "snow_cm": "Snow", "gust_max_kmh": "Gusts"}
# "Then and now": each card's title names the check plainly.
THEN_AND_NOW_TITLE = {"rain_mm": "Rain in 24 hours", "recent_rain_mm": "Rain over 6 days",
                      "feels_like_max_c": "Feels-like heat", "feels_like_min_c": "Feels-like cold",
                      "snow_cm": "Snow in 24 hours", "gust_max_kmh": "Wind gusts"}
NONE_FORECAST = {"rain_mm", "snow_cm"}  # "Snow  none forecast" (no rate for nothing)


# ---- the hero line ------------------------------------------------------------

def hero_history_range(date, today=None):
    """The history `risk.assess` reads for this date: from the record's start to the day before the date."""
    today = today or dt.date.today()
    rec_start, rec_end = risk.recent_window(date)
    return dt.date(min(risk.BASELINE_START_YEAR, rec_start.year), 1, 1), min(rec_end, today - dt.timedelta(days=1))


def _average_year(history, column, date):
    """The average yearly total of `column` over the full calendar years before the date's year, or None.

    A year missing more than risk.MAX_MISSING_SHARE of its days is left out; fewer than
    risk.RECENT_WINDOW_YEARS good years left is too thin (None, never a guess).
    """
    df = history[history["date"].dt.year < date.year]
    years = df.groupby(df["date"].dt.year)[column].agg(["sum", "count"])
    days_in_year = pd.Series([366 if pd.Timestamp(y, 12, 31).dayofyear == 366 else 365 for y in years.index],
                             index=years.index)
    good = years[years["count"] >= days_in_year * (1 - risk.MAX_MISSING_SHARE)]
    return float(good["sum"].mean()) if len(good) >= risk.RECENT_WINDOW_YEARS else None


def hero_line(result, history):
    """The bold line in the level box on raised days (Elevated, High, Extreme), from the check that set the level.

    Rain (24 h or 6 days) and snow: the value as a share of an average year's total here, only when it is
    HERO_MIN_SHARE_PERCENT or more (else None). Heat, cold and wind:
    the last year a day at least this extreme happened here. None on Typical and Not enough data days, when the
    history is too thin, or when the last such day was less than HERO_RECENT_DAYS before the date.
    """
    if result["level"] not in risk.LEVELS[1:] or history is None or history.empty:
        return None
    c = deciding_check(result)
    if c is None:
        return None
    key, value = c["key"], c["value"]
    known = history.dropna(subset=[HERO_SHARE_COLUMN.get(key, key)])
    if known.empty:
        return None
    first_year = known["date"].min().year
    if key in HERO_SHARE:
        noun, tail = HERO_SHARE[key]
        average = _average_year(history, HERO_SHARE_COLUMN[key], result["date"])
        if average is None:
            return None
        if average <= 0:  # an average year here has none at all
            return f"More {noun} than any {'day' if key != risk.RECENT_RAIN_KEY else f'{_DAYS} days'} here " \
                   f"since {first_year}"
        share = 100 * value / average
        if share >= 100:
            return f"More than a year's {noun}{tail}"
        if share < HERO_MIN_SHARE_PERCENT:  # a small share could sound mild on a raised day: no hero line
            return None
        return f"About {min(round(share), 99)}% of a year's {noun}{tail}"
    since, never = HERO_SINCE[key]
    values = known[key]
    hits = known[values <= value] if c.get("lower_is_worse") else known[values >= value]
    if hits.empty:
        return never.format(year=first_year)
    last = hits["date"].max().date()
    if (result["date"] - last).days < HERO_RECENT_DAYS:
        return None
    return since.format(year=last.year)


# ---- "Then and now" cards -------------------------------------------------------

def _rain_source(rain):
    """How the earlier days' rain is known: "measured", "forecast" or "from past forecasts"."""
    if rain["source"] == "forecast":
        return "forecast"
    if rain["source"].startswith("history"):
        return "measured"
    return "from past forecasts"


def _rain_parts(rain):
    """Where the 6-day total comes from: "36.7 mm measured + the day's forecast", "forecast for all 6 days"."""
    if rain.get("before_total") is None:
        return "including the day's forecast"
    if _rain_source(rain) == "forecast":
        return f"forecast for all {_DAYS} days"
    return f"{rain['before_total']:.1f} mm {_rain_source(rain)} + the day's forecast"


def _value_note(c, result):
    """The small words after a card's value: "forecast", with its danger line when crossed, unless the level box
    already names this check (and so its danger line): never said twice on a page."""
    if c["key"] == risk.RECENT_RAIN_KEY:
        return _rain_parts(c)
    named = c["name"] in (result.get("decided_by") or [])
    return "forecast" + ("" if named else _danger_text(c))


def less_common_now(c):
    """True when days like this were more frequent in the comparison period (or seen then, not recently)."""
    return (bool(c["baseline"]["count"]) and not c["recent"]["count"]) or (c["ratio"] is not None and c["ratio"] < 0.95)


def _events(c):
    """Such days (or wet spells) in both periods together."""
    return c["recent"]["count"] + c["baseline"]["count"]


def _count_text(count, years, never_text):
    """"7 times in 30 years", "once in 30 years", or the engine's "not seen in …" for none."""
    if not count:
        return never_text
    return f"{'once' if count == 1 else f'{count} times'} in {years:.0f} years"


def _card(check, result):
    """One check's card (widths are filled in by then_and_now, on one scale for the whole section).

    rows: now first, then the comparison period (label, per_year, words). Counts ("2 times in 30 years") when
    either period has fewer than ENOUGH_EVENTS such days (or wet spells), else the engine's rate. No rows when
    neither period saw it: `never` says so instead.
    """
    few = min(check["recent"]["count"], check["baseline"]["count"]) < ENOUGH_EVENTS
    never = _events(check) == 0
    periods = [(f"Now ({result['recent_label']})", check["recent"], check["recent_text"]),
               (result["baseline_label"], check["baseline"], check["baseline_text"])]
    rows = [] if never else [
        {"label": label, "per_year": p["per_year"], "width": 0.0,
         "words": _count_text(p["count"], p["years"], words) if few else words}
        for label, p, words in periods]
    return {"check": check, "key": check["key"], "name": check["name"], "title": THEN_AND_NOW_TITLE[check["key"]],
            "chip": None if check["level"] == "Typical" else check["level"],
            "value": amount(check["value"], check["unit"]), "value_note": _value_note(check, result),
            "counts": few, "rows": rows,
            "never": NEVER_SEEN.format(noun=NOUN[check["key"]]) if never else None,
            "rarer_now": RARER_NOW.format(noun=NOUN[check["key"]])
            if less_common_now(check) and _events(check) >= ENOUGH_EVENTS else None}


def card_checks(result):
    """The checks shown as cards, worst level first, then rarest first (engine order on a tie).

    Every check at Elevated or higher (also on a Not enough data day, so a raised reading is never hidden).
    On a Typical day: only checks that happen fewer than THEN_AND_NOW_TYPICAL_BELOW_PER_YEAR times a year now.
    """
    checks = [c for c in result["checks"] if "recent" in c]
    if result["level"] == "Typical":
        chosen = [c for c in checks if c["recent"]["per_year"] < THEN_AND_NOW_TYPICAL_BELOW_PER_YEAR]
    else:
        chosen = [c for c in checks if c["level"] in risk.LEVELS[1:]]
    return sorted(chosen, key=lambda c: (-risk.LEVELS.index(c["level"]), c["recent"]["per_year"]))


def then_and_now(result):
    """The "Then and now" cards (none: the section is hidden).

    The bars share one scale across the section: the most frequent row gets width 1.0, every other row its
    rate divided by that one.
    """
    cards = [_card(c, result) for c in card_checks(result)]
    top = max((r["per_year"] for card in cards for r in card["rows"]), default=0)
    for card in cards:
        for r in card["rows"]:
            r["width"] = r["per_year"] / top if top else 0.0
    return cards


# ---- "Other checks" / "All checks" ---------------------------------------------------

def checks_heading(result):
    """"Other checks (4)" under the cards, "All checks (6)" when there are none. n counts every check line."""
    n = len(normal_lines(result)) + len(not_enough_lines(result))
    return f"{'Other' if card_checks(result) else 'All'} checks ({n})"


def normal_lines(result):
    """(key, label, value) for each check not shown as a card, in the engine's order.

    "normal for here" after the value when the check happens at least NORMAL_FROM_PER_YEAR times a year now;
    a rarer one keeps its rate instead. Checks with not enough data are in not_enough_lines.
    """
    shown = {id(c) for c in card_checks(result)}
    lines = []
    for c in result["checks"]:
        if id(c) in shown or c["level"] == risk.NOT_ENOUGH:
            continue
        label = NORMAL_LABEL[c["key"]]
        if c["key"] in NONE_FORECAST and c["value"] == 0:
            lines.append((c["key"], label, "none forecast"))
            continue
        value = amount(c["value"], c["unit"])
        if c["key"] == "gust_max_kmh":
            value = f"up to {value}"
        if c["key"] == risk.RECENT_RAIN_KEY and _rain_source(c) != "forecast" and c.get("before_total") is not None:
            value += f" ({_rain_parts(c)})"
        if c["recent"]["per_year"] < NORMAL_FROM_PER_YEAR:
            value += f" · {c['recent_text']}"
        else:
            value += ", normal for here"
        lines.append((c["key"], label, value))
    return lines


def not_enough_lines(result):
    """"Gusts: not enough data." for each check the engine couldn't run."""
    return [f"{NORMAL_LABEL[c['key']]}: not enough data." for c in result["checks"] if c["level"] == risk.NOT_ENOUGH]


def data_notes(result):
    """The engine's notes about the data: each check's own, then the result's (not the always-shown ones)."""
    return [n for c in result["checks"] for n in c["notes"]] \
        + result["notes"][: len(result["notes"]) - len(risk.ALWAYS_NOTES)]


def _ascii(text):
    text = text.replace("–", "-").replace("—", "-")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _sms_level(level):
    return TYPICAL_SCOPE if level == "Typical" else f"{level} risk"


def sms_text(result, place, special=None):
    """A text message of at most 160 characters (plain ASCII, so it stays one SMS).

    Always says "Groundtruth" and the date. To fit, the number goes first, then the place name is
    shortened, then left out. The ice note, what a Typical day doesn't check, the short action and the
    official-warnings line are never dropped.
    """
    place = _ascii(place).strip() or "your area"
    day = _ascii(day_text(result["date"]))
    level = result["level"]
    ice = bool(ice_note(result))

    if level not in risk.LEVELS:
        must, details = ["Not enough data - check official sources."], [""]
        head = "Groundtruth {place}" + f" {day}:"
    else:
        check = deciding_check(result)
        detail = ""
        if check is not None and level != "Typical":
            unit = _ascii(check["unit"]).strip() or "C"  # "°C" -> "C"
            when = "incl. forecast" if check["key"] == risk.RECENT_RAIN_KEY else "forecast"
            detail = f"{SHORT_NAMES[check['key']]} {amount(check['value'], unit)} {when}."
        limits = TYPICAL_SMS_LIMITS_GEOLOGICAL if special == "geological" else TYPICAL_SMS_LIMITS
        if level == "Typical":
            # With ice: "Roads may be icy; ice, storms, landslides not checked." (ice said once, no contradiction)
            middle = [ICE_SMS_TYPICAL + limits.replace("Storms, ice,", "ice, storms,") if ice else limits]
        else:
            middle = [ICE_SMS if ice else "", sms_action(result) or ""]
        must = [*middle, "Check official warnings."]
        details = [detail, ""]
        head = "Groundtruth {place}" + f" {day}: {_sms_level(level)}."

    def build(where, detail, parts=must):
        return " ".join(p for p in (head.format(place=where), detail, *parts) if p).replace("Groundtruth  ",
                                                                                          "Groundtruth ")

    for detail in details:
        text = build(place, detail)
        if len(text) <= SMS_LIMIT:
            return text
    # Shorten the place name, then leave it out.
    for n in range(len(place) - 1, 0, -1):
        text = build(place[: n - 1].rstrip() + ".", "")
        if len(text) <= SMS_LIMIT:
            return text
    text = build("", "")
    if len(text) <= SMS_LIMIT:
        return text
    # Last resort (ice and the glacier note together): a shorter last line.
    return build("", "", [*must[:-1], "See official warnings."])
