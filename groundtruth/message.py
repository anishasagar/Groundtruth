"""Plain-language text built from the risk engine's numbers (no language model).

Nothing here decides a level or invents a number: it only puts what `risk.assess`
returned into words. Never uses the words "safe", "no risk" or "all clear", and
never says climate change caused anything.
"""

import datetime as dt
import unicodedata

import pandas as pd

from groundtruth import risk

OFFICIAL_LINE = "Check your official weather warnings — Groundtruth never replaces them."

# What we check and what we don't (shown in "How sure are we"). Storms get their own callout.
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
ICE_SMS = "Roads may be icy; ice itself isn't checked."
ICE_SMS_TYPICAL = "Roads may be icy; "  # + the not-checked list, starting with ice (one sentence, so it fits)
ICE_IF_AT_OR_BELOW_C = 1.0  # a margin: black ice forms with air just above 0 °C over frozen ground

# "What it means" (written by code on every day, also next to Claude's text).
NOT_COVERED_LINE = ("These checks don't cover thunderstorms, hail, freezing rain or ice, wildfire, air quality, "
                    "coastal flooding, or geological hazards.")
STORM_SENTENCE = "Storms are a major cause of weather deaths, so check your official weather and storm warnings."
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


def what_it_means(result, special=None):
    """What this means for a decision, written by code on every day (also next to Claude's text).

    Typical: what the checks don't cover first. Other levels: the action line first. Then the ice note,
    the special note ("storm" or "geological", replays.SPECIAL_NOTES), and official warnings, once, last.
    """
    if result["level"] not in risk.LEVELS:
        return template_sentence(result)
    parts = [NOT_COVERED_LINE if result["level"] == "Typical" else action_line(result)]
    parts.append(ice_note(result))
    if special == "geological":
        parts.append(GEOLOGICAL_NOTE)
    parts.append(STORM_SENTENCE if special == "storm" else OFFICIAL_LINE)
    return " ".join(p for p in parts if p)


def template_sentence(result, today=None):
    """Headline, one action line (not for Typical), the ice note if any, then the official-warnings line."""
    today = today or dt.date.today()
    level = result["level"]
    if level not in risk.LEVELS:
        return f"{risk.NOT_ENOUGH_TEXT}. Groundtruth never replaces official weather warnings."
    parts = [HEADLINES[level].format(when="today" if result["date"] == today else "on this day")]
    action = action_line(result)
    if action:
        parts.append(action)
    if ice_note(result):
        parts.append(ice_note(result))
    parts.append(OFFICIAL_LINE)
    return " ".join(parts)


LEAD = {  # how a check that is Elevated or higher opens its bullet, and what "like this" refers to
    "rain_mm": ("Forecast rain of {v} in 24 h", "Rain"),
    "recent_rain_mm": ("Rain of {v} over {n} days, including the forecast for the day", "A wet spell"),
    "feels_like_max_c": ("Forecast to feel like {v}", "Heat"),
    "feels_like_min_c": ("Forecast to feel as cold as {v}", "Cold"),
    "snow_cm": ("Forecast snowfall of {v} in 24 h", "Snow"),
    "gust_max_kmh": ("Forecast gusts up to {v}", "Wind"),
}
HOW_COMMON = {"Typical": "common", "Elevated": "uncommon", "High": "rare", "Extreme": "very rare"}


def _days(c, text):
    """"about 48 times a year" -> "about 48 days a year" (whole days, not wet spells)."""
    return text if c["key"] == risk.RECENT_RAIN_KEY else text.replace(" times a year", " days a year")


def _unusual_bullet(c, result):
    """Value, danger line (if crossed), how often it happens here, and the comparison with the baseline."""
    lead, noun = LEAD[c["key"]]
    lead = lead.format(v=amount(c["value"], c["unit"]), n=risk.RECENT_RAIN_DAYS_BEFORE + 1)
    line = c.get("danger_line")
    if c.get("crosses_danger_line"):
        how = "above" if c["value"] > line else "at"
        danger = f" — {how} the {line} {c['unit']} danger line"
    else:
        danger = ""
    text = f"**{lead}**{danger}. "

    recent, ratio_text = c["recent"], c["ratio_text"]
    years = risk.RECENT_WINDOW_YEARS
    not_less = f"but that doesn't make today any less serious: the level is based on the recent {years} years."
    if danger_line_set_level(c):  # "common here" would undercut the danger line
        often = _days(c, c["recent_text"])
        if c["ratio"] is not None and c["ratio"] < 0.95:
            return text + (f"That line matters however often this happens here: {often}. It was more frequent "
                           f"in {result['baseline_label']} ({_days(c, c['baseline_text'])}), but that doesn't "
                           "make today any less serious: the danger line sets the level.")
        ratio_text = ratio_text.replace(" here than", " than").replace(" here as", " as")
        return text + f"That line matters however often this happens here: {often}, {ratio_text}."
    if c["baseline"]["count"] and not recent["count"]:  # seen then, not seen recently
        return text + (f"Not seen in the {years} years before this date. It happened in {result['baseline_label']} "
                       f"({c['baseline_text']}), {not_less}")
    if c["ratio"] is not None and c["ratio"] < 0.95:  # less common now: must not sound reassuring
        return text + (f"{noun} like this is {HOW_COMMON[c['relative_level']]} here ({_days(c, c['recent_text'])}). "
                       f"It was more frequent in {result['baseline_label']} ({_days(c, c['baseline_text'])}), {not_less}")
    if c["ratio"] is None:  # one of the periods has no such days: the engine's own sentence says it all
        if recent["count"]:
            text += f"{noun} like this is {HOW_COMMON[c['relative_level']]} here ({c['recent_text']}); {ratio_text}."
        else:
            text += f"{ratio_text[0].upper()}{ratio_text[1:]}."
        return text
    often = _days(c, c["recent_text"])
    # "1.4 times more common than in 1951–1980" (the sentence already said "here")
    ratio_text = ratio_text.replace(" here than", " than").replace(" here as", " as")
    return text + f"{noun} like this is {HOW_COMMON[c['relative_level']]} here ({often}) and {ratio_text}."


def why_bullets(result):
    """What decided the level comes first, then the other unusual checks, then the Typical ones.

    Then the rain total for the days before the date, and last that the day's figures are a forecast.
    """
    def rank(c):  # higher = shown earlier; "Not enough data" sits just above Typical
        return risk.LEVELS.index(c["level"]) if c["level"] in risk.LEVELS else 0.5
    by_key = {c["key"]: c for c in result["checks"]}
    heat, cold = by_key.get("feels_like_max_c"), by_key.get("feels_like_min_c")
    # "Normal temperatures" only when both temperature checks are Typical; then they share one line.
    both_normal = heat is not None and cold is not None and heat["level"] == cold["level"] == "Typical"
    bullets = []
    for c in sorted(result["checks"], key=lambda c: -rank(c)):  # sorted() keeps the engine's order on ties
        if both_normal and c is cold:
            continue
        if both_normal and c is heat:
            bullets.append(f"**Temperature:** Normal temperatures for here "
                           f"(feels like {cold['value']:.0f} to {heat['value']:.0f} °C)")
        elif c["level"] == risk.NOT_ENOUGH:
            bullets.append(f"**{c['name']}:** {risk.NOT_ENOUGH_TEXT}")
        elif c["level"] == "Typical":
            bullets.append(f"**{c['name']}:** {c['text']}")
        else:
            bullets.append(_unusual_bullet(c, result))
    rain = result["checks"][-1]
    days = risk.RECENT_RAIN_DAYS_BEFORE
    if rain.get("before_total") is None:
        bullets.append(f"**Rain in the {days} days before:** not available")
    else:
        forecast = " (forecast)" if rain["source"] == "forecast" else ""
        bullets.append(f"**Rain in the {days} days before:** {rain['before_total']:.1f} mm{forecast}")
    bullets.append(f"**About these figures:** {FORECAST_NOTE}")
    return bullets


def rarity_rows(result):
    """(rows, check name, what "like this" means) for the "how often" lines, or None when hidden.

    Hidden for Typical and for Not enough data. Each row: label (period), per_year,
    width (0-1, the more frequent period is 1), words (the engine's wording).
    """
    if result["level"] in ("Typical", risk.NOT_ENOUGH) or result["level"] not in risk.LEVELS:
        return None
    check = deciding_check(result)
    if check is None:
        return None
    periods = [(result["baseline_label"], check["baseline"], check["baseline_text"]),
               (result["recent_label"], check["recent"], check["recent_text"])]
    top = max(p["per_year"] for _, p, _ in periods)
    rows = [{"label": label, "per_year": p["per_year"], "width": (p["per_year"] / top) if top else 0.0,
             "words": words}
            for label, p, words in periods]
    return rows, check["name"], LIKE_THIS[check["key"]]


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
