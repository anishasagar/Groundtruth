"""The risk engine: turns weather numbers into a risk level.

Code computes every number and the level here. Nothing in this file uses a
language model.
"""

import datetime as dt

import pandas as pd

from groundtruth.weather import get_forecast_day, get_forecast_range, get_history

# =============================================================================
# SETTINGS — change the time periods and thresholds here, and only here.
# Every label the app shows (like "1951–1980") is built from these values.
# =============================================================================

# Comparison period: "days like this are X times more common than in ...".
BASELINE_START_YEAR = 1951
BASELINE_END_YEAR = 1980

# The level is judged on this many years, ending the day before the date.
RECENT_WINDOW_YEARS = 30

# Recent-rain total = this many days before the date, plus the date itself.
RECENT_RAIN_DAYS_BEFORE = 5

# Absolute danger lines. Crossing one = at least High.
DANGER_LINES = {
    "rain_mm": 150,  # mm in 24 h
    "feels_like_max_c": 40,  # °C
    "gust_max_kmh": 100,  # km/h
}

# Relative level, from "about once every N years" in the recent window:
#   more often than once every 1 year  -> Typical
#   every 1 to 5 years                 -> Elevated
#   every 5 to 20 years                -> High
#   rarer than every 20 years, or never -> Extreme
# On an exact border the higher level wins (when unsure, choose higher).
TYPICAL_IF_MORE_OFTEN_THAN_YEARS = 1
ELEVATED_IF_MORE_OFTEN_THAN_YEARS = 5
HIGH_IF_MORE_OFTEN_THAN_YEARS = 20

# A history window with more missing days than this share counts as thin data.
MAX_MISSING_SHARE = 0.10

# =============================================================================

LEVELS = ["Typical", "Elevated", "High", "Extreme"]
NOT_ENOUGH = "Not enough data"
NOT_ENOUGH_TEXT = "Not enough data — check official sources"

CHECKS = {
    "rain_mm": ("Rain (24 h)", "mm"),
    "feels_like_max_c": ("Feels-like heat", "°C"),
    "gust_max_kmh": ("Wind gust", "km/h"),
}
RECENT_RAIN_NAME = f"Recent rain ({RECENT_RAIN_DAYS_BEFORE + 1}-day total)"
RECENT_RAIN_KEY = "recent_rain_mm"

ALWAYS_NOTES = [
    "Check your official weather warnings. Groundtruth never replaces them.",
    "The history data is a ~25 km grid and misses very local storms.",
    "Groundtruth covers weather-driven hazards only. For landslides, glacier collapse "
    "or earthquakes, check local civil protection and geological authorities.",
]


# ---- labels (all built from the settings) -----------------------------------

def baseline_label():
    return f"{BASELINE_START_YEAR}–{BASELINE_END_YEAR}"


def baseline_years():
    return BASELINE_END_YEAR - BASELINE_START_YEAR + 1


def recent_window(date):
    """The RECENT_WINDOW_YEARS years ending the day before `date`."""
    try:
        start = date.replace(year=date.year - RECENT_WINDOW_YEARS)
    except ValueError:  # 29 February
        start = date.replace(year=date.year - RECENT_WINDOW_YEARS, day=28)
    return start, date - dt.timedelta(days=1)


def recent_label(date):
    start, end = recent_window(date)
    return f"{start.year}–{end.year}"


def recent_phrase():
    return f"the {RECENT_WINDOW_YEARS} years before this date"


# ---- counting ---------------------------------------------------------------

def _rarity(dates, values, threshold, start, end, nominal_years, spell_days=1):
    """How often a value >= threshold happened between start and end.

    Returns None if the window is missing too many days (thin data).
    spell_days: for multi-day totals (e.g. 6), overlapping windows from the
    same wet spell would count one wet week six times. So a run of back-to-back
    qualifying days counts as one event per `spell_days` days it lasts.
    """
    expected_days = (end - start).days + 1
    in_window = (dates >= pd.Timestamp(start)) & (dates <= pd.Timestamp(end))
    window = values[in_window]
    valid_days = int(window.notna().sum())
    if expected_days <= 0 or valid_days < expected_days * (1 - MAX_MISSING_SHARE):
        return None

    hits = (window >= threshold).astype(bool)
    if spell_days > 1:
        run_id = (hits != hits.shift(1)).cumsum()
        run_lengths = hits[hits].groupby(run_id[hits]).size()
        count = int(sum(-(-n // spell_days) for n in run_lengths))  # rounded up
    else:
        count = int(hits.sum())
    years = nominal_years * min(valid_days / expected_days, 1)
    return {
        "count": count,
        "years": years,
        "per_year": count / years,
        "every_n_years": (years / count) if count else None,
    }


def _num(x):
    return f"{x:.1f}" if x < 10 else f"{x:.0f}"


def _how_often(r, never_text):
    if r["count"] == 0:
        return never_text
    n = r["every_n_years"]
    if n < 1:
        return f"about {_num(r['per_year'])} times a year"
    if n < 1.05:
        return "about once a year"
    return f"about once every {_num(n)} years"


def _ratio(base, recent):
    """Recent rate ÷ baseline rate, plus the sentence that says it."""
    b, r = base["count"], recent["count"]
    if b and r:
        ratio = recent["per_year"] / base["per_year"]
        if 0.95 <= ratio < 1.05:
            return ratio, f"about as common here as in {baseline_label()}"
        if ratio >= 1:
            return ratio, f"{_num(ratio)} times more common here than in {baseline_label()}"
        return ratio, f"{_num(1 / ratio)} times less common here than in {baseline_label()}"
    if r:
        return None, f"not seen in {baseline_label()}, but seen {r} times in {recent_phrase()}"
    if b:
        return None, f"seen in {baseline_label()}, but not in {recent_phrase()}"
    return None, f"not seen in {baseline_label()} or in {recent_phrase()}"


def _relative_level(r):
    n = r["every_n_years"]
    if n is None:
        return "Extreme"
    if n < TYPICAL_IF_MORE_OFTEN_THAN_YEARS:
        return "Typical"
    if n < ELEVATED_IF_MORE_OFTEN_THAN_YEARS:
        return "Elevated"
    if n < HIGH_IF_MORE_OFTEN_THAN_YEARS:
        return "High"
    return "Extreme"


def _typical_text(key, value):
    """Plain wording for a check that comes back Typical (no "how often" line)."""
    if key == RECENT_RAIN_KEY:
        return f"No unusual rain in the last {RECENT_RAIN_DAYS_BEFORE + 1} days ({value:.1f} mm)"
    if key == "rain_mm":
        return "No rain forecast" if value == 0 else f"Normal rain for here ({value:.1f} mm)"
    if key == "feels_like_max_c":
        return f"Normal temperatures for here (feels like {value:.0f} °C)"
    return f"Normal wind for here (gusts up to {value:.0f} km/h)"


def _unusual_text(recent, recent_text, ratio_text, crosses, danger_line, unit):
    """Wording for a check that comes back Elevated or higher."""
    if recent["count"]:
        text = f"{recent_text} in {recent_phrase()}; {ratio_text}"
    else:
        text = ratio_text  # already says it wasn't seen recently
    if crosses:
        text += f"; at or above the {danger_line} {unit} danger line"
    return text


def _worse(a, b):
    return a if LEVELS.index(a) >= LEVELS.index(b) else b


def _check(key, name, unit, value, dates, values, date, danger_line=None, spell_days=1):
    """One rarity check (plus the danger line, if there is one).

    `text` is what the app shows: plain wording when Typical, "how often" and
    the comparison with the baseline only when Elevated or higher. The full
    numbers stay in the result either way.
    """
    result = {"key": key, "name": name, "unit": unit, "value": value, "danger_line": danger_line, "notes": []}
    if value is None or pd.isna(value):
        result.update(level=NOT_ENOUGH, decided_by=None, text=NOT_ENOUGH_TEXT,
                      notes=[f"No forecast value. {NOT_ENOUGH_TEXT}."])
        return result

    base_start, base_end = dt.date(BASELINE_START_YEAR, 1, 1), dt.date(BASELINE_END_YEAR, 12, 31)
    rec_start, rec_end = recent_window(date)
    base = _rarity(dates, values, value, base_start, base_end, baseline_years(), spell_days)
    recent = _rarity(dates, values, value, rec_start, rec_end, RECENT_WINDOW_YEARS, spell_days)
    if base is None or recent is None:
        result.update(level=NOT_ENOUGH, decided_by=None, text=NOT_ENOUGH_TEXT,
                      notes=[f"History too thin. {NOT_ENOUGH_TEXT}."])
        return result

    ratio, ratio_text = _ratio(base, recent)
    relative = _relative_level(recent)
    crosses = danger_line is not None and value >= danger_line
    level = _worse(relative, "High") if crosses else relative
    if crosses and LEVELS.index("High") > LEVELS.index(relative):
        decided_by = "danger line"
    elif crosses and relative == "High":
        decided_by = "rarity and danger line"
    else:
        decided_by = "rarity"

    recent_text = _how_often(recent, f"not seen in those {RECENT_WINDOW_YEARS} years")
    if level == "Typical":
        text = _typical_text(key, value)
    else:
        text = _unusual_text(recent, recent_text, ratio_text, crosses, danger_line, unit)

    result.update(
        baseline=base,
        recent=recent,
        baseline_text=_how_often(base, f"not seen in {baseline_label()}"),
        recent_text=recent_text,
        text=text,
        ratio=ratio,
        ratio_text=ratio_text,
        relative_level=relative,
        crosses_danger_line=crosses,
        level=level,
        decided_by=decided_by,
    )
    return result


# ---- recent rain ------------------------------------------------------------

def _recent_rain_days(lat, lon, date, today, hist_df, forecast_rain):
    """Rain on each of the RECENT_RAIN_DAYS_BEFORE days before `date`, plus the date.

    Returns (list of daily amounts, source text, notes).
    """
    first = date - dt.timedelta(days=RECENT_RAIN_DAYS_BEFORE)
    before = [first + dt.timedelta(days=i) for i in range(RECENT_RAIN_DAYS_BEFORE)]

    if date >= today:
        fc = get_forecast_range(lat, lon, first, date, today)["data"]
        amounts = [None if pd.isna(v) else float(v) for v in fc["rain_mm"]]
        if len(amounts) != RECENT_RAIN_DAYS_BEFORE + 1:
            amounts = [None] * (RECENT_RAIN_DAYS_BEFORE + 1)
        return amounts, "forecast", ["This assumes the forecast rain actually falls."]

    # Past date: what actually fell on the earlier days (ERA5), if ERA5 has them.
    by_day = hist_df.set_index(hist_df["date"].dt.date)["rain_mm"]
    amounts = [by_day.get(d) for d in before]
    amounts = [None if a is None or pd.isna(a) else float(a) for a in amounts]
    notes = []
    source = "history (ERA5) for the earlier days"
    if any(a is None for a in amounts):
        fc = get_forecast_range(lat, lon, first, before[-1], today)["data"]
        amounts = [None if pd.isna(v) else float(v) for v in fc["rain_mm"]]
        source = "past forecasts for the earlier days"
        notes.append("The history record doesn't have the earlier days yet, so past forecasts were used.")
    return amounts + [forecast_rain], source, notes


# ---- the assessment ---------------------------------------------------------

def assess(lat, lon, date, today=None):
    """Assess one place and date. Returns a dict with every check and the final level."""
    today = today or dt.date.today()
    rec_start, rec_end = recent_window(date)
    hist_start = dt.date(min(BASELINE_START_YEAR, rec_start.year), 1, 1)
    hist_end = min(rec_end, today - dt.timedelta(days=1))

    fc = get_forecast_day(lat, lon, date, today)
    hist = get_history(lat, lon, hist_start, hist_end)
    df = hist["data"]

    checks = []
    for key, (name, unit) in CHECKS.items():
        checks.append(_check(key, name, unit, fc[key], df["date"], df[key], date, DANGER_LINES[key]))

    # Recent rain: the same rarity check on multi-day totals.
    days = RECENT_RAIN_DAYS_BEFORE + 1
    amounts, rain_source, rain_notes = _recent_rain_days(lat, lon, date, today, df, fc["rain_mm"])
    have_all = all(a is not None for a in amounts)
    total = sum(amounts) if have_all else None
    before_total = sum(amounts[:-1]) if all(a is not None for a in amounts[:-1]) else None
    rolling = df["rain_mm"].rolling(days, min_periods=days).sum()
    rain_check = _check(RECENT_RAIN_KEY, RECENT_RAIN_NAME, "mm", total, df["date"], rolling, date,
                        spell_days=days)
    rain_check["before_total"] = before_total
    rain_check["daily_amounts"] = amounts
    rain_check["source"] = rain_source
    rain_check["notes"] = rain_check["notes"] + rain_notes
    checks.append(rain_check)

    # Final level: the worst of all checks.
    available = [c for c in checks if c["level"] != NOT_ENOUGH]
    missing = [c["name"] for c in checks if c["level"] == NOT_ENOUGH]
    worst = None
    for c in available:
        worst = c["level"] if worst is None else _worse(worst, c["level"])

    notes = []
    if missing and (worst is None or LEVELS.index(worst) < LEVELS.index("High")):
        level = NOT_ENOUGH
        decided_by = []
        notes.append(f"{NOT_ENOUGH_TEXT}. Missing: {', '.join(missing)}.")
    else:
        level = worst
        decided_by = [c["name"] for c in available if c["level"] == worst]
        if missing:
            notes.append(f"Some data was missing ({', '.join(missing)}); the level shown comes from the rest.")

    return {
        "latitude": lat,
        "longitude": lon,
        "date": date,
        "level": level,
        "decided_by": decided_by,
        "checks": checks,
        "baseline_label": baseline_label(),
        "recent_label": recent_label(date),
        "recent_phrase": recent_phrase(),
        "forecast_source": fc["source"],
        "forecast_grid_point": fc["grid_point"],
        "history_source": hist["source"],
        "history_grid_point": hist["grid_point"],
        "notes": notes + ALWAYS_NOTES,
    }
