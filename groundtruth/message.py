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

# {when} becomes "today", or "on this day" when the date isn't today (replays, other dates).
HEADLINES = {
    "Typical": "Weather here {when} is typical for this place.",
    "Elevated": "Risk here {when} is higher than usual.",
    "High": "Risk here {when} is unusually high.",
    "Extreme": "Risk here {when} is extremely high.",
}

# One fixed action line per hazard. None for Typical.
ACTIONS = {
    "rain": "Avoid underpasses, low roads and riverbanks.",
    "heat": "Avoid heavy exertion outdoors, drink water, and check on older or vulnerable people.",
    "wind": "Secure loose objects and stay away from trees.",
}
HAZARD_OF_CHECK = {"rain_mm": "rain", "recent_rain_mm": "rain", "feels_like_max_c": "heat", "gust_max_kmh": "wind"}

SHORT_NAMES = {"rain_mm": "Rain", "recent_rain_mm": "6-day rain", "feels_like_max_c": "Feels-like", "gust_max_kmh": "Gusts"}

SMS_LIMIT = 160


def day_text(date):
    return f"{date.day} {date:%b %Y}"


def _amount(value, unit):
    return f"{value:.1f} {unit}" if value < 10 else f"{value:.0f} {unit}"


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
    "gust_max_kmh": ("Gusts up to {v}", "Wind"),
}
HOW_COMMON = {"Typical": "common", "Elevated": "uncommon", "High": "rare", "Extreme": "very rare"}


def _unusual_bullet(c, result):
    """Value, danger line (if crossed), how often it happens here, and the comparison with the baseline."""
    lead, noun = LEAD[c["key"]]
    lead = lead.format(v=_amount(c["value"], c["unit"]), n=risk.RECENT_RAIN_DAYS_BEFORE + 1)
    line = c.get("danger_line")
    if c.get("crosses_danger_line"):
        how = "above" if c["value"] > line else "at"
        danger = f" — {how} the {line} {c['unit']} danger line"
    else:
        danger = ""
    text = f"**{lead}**{danger}. "

    recent, ratio_text = c["recent"], c["ratio_text"]
    if c["ratio"] is None:  # one of the periods has no such days: the engine's own sentence says it all
        if recent["count"]:
            text += f"{noun} like this is {HOW_COMMON[c['relative_level']]} here ({c['recent_text']}); {ratio_text}."
        else:
            text += f"{ratio_text[0].upper()}{ratio_text[1:]}."
        return text
    often = c["recent_text"]
    if c["key"] != "recent_rain_mm":  # whole days, not spells
        often = often.replace(" times a year", " days a year")
    # "1.4 times more common than in 1951–1980" (the sentence already said "here")
    ratio_text = ratio_text.replace(" here than", " than").replace(" here as", " as")
    return text + f"{noun} like this is {HOW_COMMON[c['relative_level']]} here ({often}) and {ratio_text}."


def why_bullets(result):
    """What decided the level comes first, then the other unusual checks, then the Typical ones.

    The last line is the rain total for the days before the date.
    """
    def rank(c):  # higher = shown earlier; "Not enough data" sits just above Typical
        return risk.LEVELS.index(c["level"]) if c["level"] in risk.LEVELS else 0.5
    bullets = []
    for c in sorted(result["checks"], key=lambda c: -rank(c)):  # sorted() keeps the engine's order on ties
        if c["level"] == risk.NOT_ENOUGH:
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
    """(rows, check name) for the "how often" lines, or None when they should be hidden.

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
    return rows, check["name"]


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
            detail = f"{SHORT_NAMES[check['key']]} {_amount(check['value'], unit)}."
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
