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

# {when} becomes "today", or "on this day" when the date isn't today (replays, other dates).
HEADLINES = {
    "Typical": "Normal conditions for here, for the rain, temperature, snow and wind we check.",
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


def action_line(result):
    if result["level"] == "Typical":
        return None
    check = deciding_check(result)
    return ACTIONS.get(HAZARD_OF_CHECK.get(check["key"])) if check else None


def template_sentence(result, today=None):
    """Headline, one action line (not for Typical), then the official-warnings line."""
    today = today or dt.date.today()
    level = result["level"]
    if level not in risk.LEVELS:
        return f"{risk.NOT_ENOUGH_TEXT}. Groundtruth never replaces official weather warnings."
    parts = [HEADLINES[level].format(when="today" if result["date"] == today else "on this day")]
    action = action_line(result)
    if action:
        parts.append(action)
    parts.append(OFFICIAL_LINE)
    return " ".join(parts)


LEAD = {  # how a check that is Elevated or higher opens its bullet, and what "like this" refers to
    "rain_mm": ("Rain of {v} in 24 h", "Rain"),
    "recent_rain_mm": ("Rain of {v} over {n} days", "A wet spell"),
    "feels_like_max_c": ("Feels like {v}", "Heat"),
    "feels_like_min_c": ("Feels as cold as {v}", "Cold"),
    "snow_cm": ("Snowfall of {v} in 24 h", "Snow"),
    "gust_max_kmh": ("Gusts up to {v}", "Wind"),
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

    The last line is the rain total for the days before the date.
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


def sms_text(result, place):
    """A text message of at most 160 characters (plain ASCII, so it stays one SMS)."""
    place = _ascii(place).strip() or "your area"
    day = _ascii(day_text(result["date"]))
    level = result["level"]

    if level not in risk.LEVELS:
        candidates = [f"Groundtruth {place} {day}: Not enough data - check official sources."]
    else:
        word = "weather" if level == "Typical" else "risk"
        head = f"Groundtruth {place} {day}: {level} {word}."
        tail = "Check official warnings."
        check = deciding_check(result)
        detail = ""
        if check is not None and level != "Typical":
            unit = _ascii(check["unit"]).strip() or "C"  # "°C" -> "C"
            detail = f"{SHORT_NAMES[check['key']]} {amount(check['value'], unit)}."
        action = action_line(result)
        candidates = [
            " ".join(p for p in (head, detail, action, tail) if p),
            " ".join(p for p in (head, detail, tail) if p),
            f"{head} {tail}",
        ]

    for text in candidates:
        if len(text) <= SMS_LIMIT:
            return text
    # Last resort: shorten the place name.
    for n in range(len(place), 0, -1):
        short = place[: n - 1] + "." if n < len(place) else place
        text = (f"Groundtruth {short} {day}: {level} risk. Check official warnings." if level in risk.LEVELS
                else f"Groundtruth {short} {day}: Not enough data - check official sources.")
        if len(text) <= SMS_LIMIT:
            return text
    return ("Groundtruth: Not enough data - check official sources." if level not in risk.LEVELS
            else f"Groundtruth: {level} risk. Check official warnings.")
