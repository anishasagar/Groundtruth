"""Plain-language text built from the risk engine's numbers (no language model).

Nothing here decides a level or invents a number: it only puts what `risk.assess`
returned into words. Never uses the words "safe", "no risk" or "all clear", and
never says climate change caused anything.
"""

import datetime as dt
import unicodedata

import pandas as pd

from groundtruth import risk

# The first line of "How sure are we". The visible pointer to official warnings is STORM_LINE.
OFFICIAL_LINE = risk.ALWAYS_NOTES[0]
# The yellow line on every result: the page's one visible pointer to official warnings.
STORM_LINE = "Thunderstorms aren't checked. Follow official weather and storm warnings."

# The line under the level word on a Typical day: what is typical (never "Typical weather").
TYPICAL_LEVEL_LINE = "for rain, temperature, snow and wind"
# Shown on every Typical day, right under the level box. Thunderstorms are in STORM_LINE, so not here; with the
# ice line (ICE_SMS) right above it, ice isn't repeated either.
TYPICAL_LIMITS = "These checks can't see ice on roads, landslides or glacier collapse."
TYPICAL_LIMITS_ICE = "These checks can't see landslides or glacier collapse."
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
# "Then and now", when the check is less common now than in the comparison period.
RARER_NOW = "{noun} like this is rarer here now, so people and places may be less prepared for it."
# On Typical days RARER_NOW is shown only for a check that happens fewer than this many times a year now
# (Paris snow, about 1.1: yes; a few tenths of a mm of rain, about 45: no). Raised days always show it.
RARER_NOW_TYPICAL_BELOW_PER_YEAR = 5
# When either period has fewer than this many such days (or wet spells), the two rows can't show a change.
TOO_FEW_TO_COMPARE_BELOW = 5
TOO_FEW_LINE = "Too few days like this in either period to say whether it has changed."
ARROW = "→ "

# Part of the facts sent to Claude (and so of each saved reply's fingerprint). Not shown on the page.
SCOPE_LINE = ("We check rain, heat, cold, snow, wind and recent rain. We don't yet check thunderstorms, "
              "hail, freezing rain or ice, wildfire, air quality, coastal flooding, or geological hazards. "
              "For those, follow official warnings.")
STORM_NOTE = ("**Thunderstorms are not checked.** Storms are a major cause of weather deaths — "
              "follow official storm warnings.")
GEOLOGICAL_NOTE = ("Groundtruth covers weather-driven hazards only. For geological hazards (landslides, "
                   "glacier collapse, earthquakes), check local civil protection and geological authorities.")

# {when} becomes "today", or "on this day" when the date isn't today (replays, other dates).
# Typical says what is typical, never a whole-day verdict, and names what the checks can't see.
HEADLINES = {
    "Typical": ("Typical rain, temperature, snow and wind for here. These checks can't see thunderstorms, "
                "ice on roads, or landslides and glacier collapse."),
    "Elevated": "Risk here {when} is higher than usual.",
    "High": "Risk here {when} is unusually high.",
    "Extreme": "Risk here {when} is extremely high.",
}

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

# What "a day like this" means for each check (caption under the "how often" lines).
LIKE_THIS = {
    "rain_mm": "days with at least this much rain",
    "recent_rain_mm": "wet spells at least this wet",
    "feels_like_max_c": "days at least this hot",
    "feels_like_min_c": "days at least this cold",
    "snow_cm": "days with at least this much snow",
    "gust_max_kmh": "days with gusts at least this strong",
}

SMS_LIMIT = 160
# What a Typical level covers. "Typical weather" would sound like everything is fine.
TYPICAL_SCOPE = "Typical rain, temperature, snow and wind"
# Every Typical text message ends with what isn't checked (never dropped to save space).
TYPICAL_SMS_LIMITS = "Storms, ice, landslides not checked."
TYPICAL_SMS_LIMITS_GEOLOGICAL = "Storms, ice, landslides, glacier floods not checked."

# Snow or rain on a day that drops to about freezing. Ice itself isn't checked yet (Phase 2).
ICE_NOTE = "Snow or rain on freezing ground can make roads icy, and ice isn't checked."
ICE_SMS = "Roads may be icy; ice itself isn't checked."  # also the ice line on raised days
ICE_SMS_TYPICAL = "Roads may be icy; "  # + the not-checked list, starting with ice (one sentence, so it fits)
ICE_IF_AT_OR_BELOW_C = 1.0  # a margin: black ice forms with air just above 0 °C over frozen ground

# The day's values come from a forecast, also for past days (the past-forecast archive).
FORECAST_NOTE = "The day's figures are a forecast and can be too low."
# When a danger line set the level, how often it happens here must not sound reassuring.
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
    parts = []  # "Feels like 41 °C forecast, above the 40 °C danger line"
    for name in result.get("decided_by") or []:
        c = by_name[name]
        parts.append(LEVEL_VALUE[c["key"]].format(v=amount(c["value"], c["unit"])) + _danger_text(c))
    return "; ".join(parts)


def _danger_text(c):
    """", above the 40 °C danger line" when the check crossed its line, else ""."""
    if not c.get("crosses_danger_line"):
        return ""
    how = "above" if c["value"] > c["danger_line"] else "at"
    return f", {how} the {c['danger_line']} {c['unit']} danger line"


def summary_lines(result, special=None):
    """The code-written lines under the level box (and the headline), in screen order.

    Raised: the action line, the ice line, the geological note. Typical: the ice line, what else the checks
    can't see, the geological note. Always last: STORM_LINE, shown in yellow, the visible pointer to
    official warnings. special: "storm" or "geological" (replays.SPECIAL_NOTES).
    """
    level = result["level"]
    ice = ice_note(result)
    if level not in risk.LEVELS:
        lines = []
    elif level == "Typical":
        lines = [ICE_SMS, TYPICAL_LIMITS_ICE] if ice else [TYPICAL_LIMITS]
    else:
        action = action_line(result)
        lines = [ARROW + action if action else None, ICE_SMS if ice else None]
    if special == "geological":
        lines.append(GEOLOGICAL_NOTE)
    return [line for line in lines if line] + [STORM_LINE]


def what_it_means(result, special=None):
    """The code-written lines under the level box as one text (summary_lines), for the test log."""
    return " ".join(summary_lines(result, special))


def template_sentence(result, today=None):
    """Headline, one action line (not for Typical) and the ice note if any. The yellow STORM_LINE follows it."""
    if result["level"] not in risk.LEVELS:
        return template_headline(result, today)
    return " ".join(p for p in (template_headline(result, today), action_line(result), ice_note(result)) if p)


def template_headline(result, today=None):
    """The headline alone, for template mode on raised days (the action and ice lines follow from summary_lines)."""
    today = today or dt.date.today()
    if result["level"] not in risk.LEVELS:
        return f"{risk.NOT_ENOUGH_TEXT}."
    return HEADLINES[result["level"]].format(when="today" if result["date"] == today else "on this day")


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
# "The numbers": label and value wording per check. {when} is "today" or "on 4 Jul 2025".
NUMBER_LABEL = {"rain_mm": "Rain {when}", "recent_rain_mm": "Rain over 6 days", "feels_like_max_c": "Feels-like high",
                "feels_like_min_c": "Feels-like low", "snow_cm": "Snow", "gust_max_kmh": "Gusts"}
NUMBER_VALUE = {"rain_mm": "{v} forecast", "recent_rain_mm": "{v}", "feels_like_max_c": "{v} forecast",
                "feels_like_min_c": "{v} forecast", "snow_cm": "{v} forecast", "gust_max_kmh": "up to {v} forecast"}
NONE_FORECAST = {"rain_mm", "snow_cm"}  # "Snow: none forecast." (no rate for nothing)


def _days(c, text):
    """"about 48 times a year" -> "about 48 days a year" (whole days, not wet spells)."""
    return text if c["key"] == risk.RECENT_RAIN_KEY else text.replace(" times a year", " days a year")


def _how_often(c, baseline_label):
    """"About once every 15 years here, about the same as in 1951–1980." from the engine's own wording."""
    now, then = _days(c, c["recent_text"]), _days(c, c["baseline_text"])
    if not c["recent"]["count"]:  # "A wet spell like this was not seen…" (says which check, so never twice)
        seen = f"{NOUN[c['key']]} like this was not seen in the {risk.RECENT_WINDOW_YEARS} years before the day"
        if c["baseline"]["count"]:
            return f"{seen}; {then} in {baseline_label}."
        return f"{seen} or in {baseline_label}."
    now = now[0].upper() + now[1:] + " here"
    if not c["baseline"]["count"]:
        return f"{now}; not seen in {baseline_label}."
    if c["ratio"] < 0.95:
        return f"{now}, down from {then} in {baseline_label}."
    if c["ratio"] < 1.05:
        return f"{now}, about the same as in {baseline_label}."
    more = c["ratio_text"].replace(" times more common here than", " times more often than")
    return f"{now}, {more}."


def _rain_before(rain, today_words):
    """"36.7 mm measured before the day, plus the day's forecast" (where the earlier days' rain came from)."""
    before, the_day = rain.get("before_total"), today_words
    if before is None:
        return None
    if rain["source"] == "forecast":
        how = "forecast"
    elif rain["source"].startswith("history"):
        how = "measured"
    else:
        how = "from past forecasts"
    return f"{before:.1f} mm {how} before {the_day[0]}, plus {the_day[1]} forecast"


def number_lines(result, today=None):
    """"The numbers": one plain line per check, in the engine's order, then the engine's data notes."""
    today = today or dt.date.today()
    is_today = result["date"] == today
    when = "today" if is_today else f"on {day_text(result['date'])}"
    the_day = ("today", "today's") if is_today else ("the day", "the day's")
    lines = []
    for c in result["checks"]:
        label = NUMBER_LABEL[c["key"]].format(when=when)
        if c["level"] == risk.NOT_ENOUGH:
            lines.append(f"{label}: not enough data.")
            continue
        if c["key"] in NONE_FORECAST and c["value"] == 0:
            lines.append(f"{label}: none forecast.")
            continue
        value = NUMBER_VALUE[c["key"]].format(v=amount(c["value"], c["unit"]))
        if c["key"] == risk.RECENT_RAIN_KEY and _rain_before(c, the_day):
            value += f" ({_rain_before(c, the_day)})"
        line = f"{label}: {value}{_danger_text(c)}. {_how_often(c, result['baseline_label'])}"
        lines.append(" ".join([line, *c["notes"]]))
    lines += result["notes"][: len(result["notes"]) - len(risk.ALWAYS_NOTES)]
    return lines


def show_rarer_now(c, level):
    """RARER_NOW applies: less common now, and on Typical days only for a check that happens < 5 times a year now."""
    return less_common_now(c) and (level != "Typical" or c["recent"]["per_year"] < RARER_NOW_TYPICAL_BELOW_PER_YEAR)


def less_common_now(c):
    """True when days like this were more frequent in the comparison period (or seen then, not recently)."""
    return (bool(c["baseline"]["count"]) and not c["recent"]["count"]) or (c["ratio"] is not None and c["ratio"] < 0.95)


def rarity_rows(result):
    """"Then and now" for the check that set the level (on Typical days, the rarest one), or None.

    None for Not enough data. A dict: rows (now first, then the comparison period; each with label,
    per_year, width 0-1 where the more frequent period is 1, and the engine's words), name, like_this,
    caption ("Rain (24 h), 107 mm forecast: how often … happen here."), too_few (TOO_FEW_LINE when either
    period has fewer than 5 such days, else None), rarer_now (RARER_NOW, or None; see show_rarer_now; never with
    too_few) and danger_note (DANGER_LINE_NOTE when a danger line set the level).
    """
    if result["level"] not in risk.LEVELS:
        return None
    check = deciding_check(result)
    if check is None:
        return None
    periods = [(f"Now ({result['recent_label']})", check["recent"], check["recent_text"]),
               (result["baseline_label"], check["baseline"], check["baseline_text"])]
    top = max(p["per_year"] for _, p, _ in periods)
    rows = [{"label": label, "per_year": p["per_year"], "width": (p["per_year"] / top) if top else 0.0,
             "words": words}
            for label, p, words in periods]
    too_few = min(check["recent"]["count"], check["baseline"]["count"]) < TOO_FEW_TO_COMPARE_BELOW
    value = amount(check["value"], check["unit"])
    return {"rows": rows, "name": check["name"], "like_this": LIKE_THIS[check["key"]],
            "caption": f"{check['name']}, {value} forecast: how often {LIKE_THIS[check['key']]} happen here.",
            "too_few": TOO_FEW_LINE if too_few else None,
            "rarer_now": RARER_NOW.format(noun=NOUN[check["key"]])
            if show_rarer_now(check, result["level"]) and not too_few else None,
            "danger_note": DANGER_LINE_NOTE if danger_line_set_level(check) else None}


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
