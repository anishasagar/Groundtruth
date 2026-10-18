"""Fetch weather numbers from Open-Meteo (no API key needed).

Three things:
- get_forecast_day: the forecast for one date (rain, max feels-like, max gust).
- get_forecast_range: the same for a run of dates (used for the recent-rain total).
- get_history: the same three values for every day in a date range, from the
  ERA5 reanalysis (~25 km grid). Downloaded history is saved in data/history/
  so each place is only downloaded once.

Missing values stay missing (None / NaN). Nothing is filled in or guessed.
"""

import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd
import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HISTORICAL_FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Open-Meteo name -> our short name
VARIABLES = {
    "precipitation_sum": "rain_mm",
    "apparent_temperature_max": "feels_like_max_c",
    "wind_gusts_10m_max": "gust_max_kmh",
}

FORECAST_DAYS_AHEAD = 16  # the Forecast API reaches about this far
HISTORY_DIR = Path(__file__).resolve().parent.parent / "data" / "history"
HISTORY_SOURCE = "Open-Meteo Historical Weather API (ERA5)"


class NotAvailable(Exception):
    """The requested data does not exist (date out of range, etc.)."""


class LimitReached(Exception):
    """Open-Meteo refused because the free daily request limit is used up."""


def _get(url, params, tries=4):
    """GET with a few retries on network errors. Raises if it still fails."""
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=120)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 429:
            raise LimitReached("Open-Meteo's free daily limit is used up. Try again tomorrow.")
        if r.status_code == 400:
            # Open-Meteo uses 400 for "date out of range" and similar.
            reason = r.json().get("reason", r.text) if r.content else "bad request"
            raise NotAvailable(reason)
        r.raise_for_status()
        return r.json()


def _params(lat, lon, start, end):
    return {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(VARIABLES),
        "timezone": "auto",  # days are local calendar days
    }


def _to_frame(data):
    daily = data.get("daily") or {}
    df = pd.DataFrame({"date": pd.to_datetime(daily.get("time", []))})
    for api_name, short in VARIABLES.items():
        df[short] = pd.to_numeric(pd.Series(daily.get(api_name, [None] * len(df))), errors="coerce")
    return df


def _grid_point(data):
    return {"latitude": data.get("latitude"), "longitude": data.get("longitude")}


def get_forecast_range(lat, lon, start, end, today=None):
    """Forecast for every date from start to end (inclusive).

    If the last date is today or later -> Forecast API (it also covers recent
    past days, so a run of days around today comes from one forecast).
    All dates in the past -> Historical Forecast API. Note: that archive
    stitches together the *most recent* model run for each hour, so it shows
    what models predicted a few hours ahead, not what a forecast issued days
    earlier said.

    Returns a dict: source, grid_point, and data (one row per date).
    Raises NotAvailable if the dates are outside what the source covers.
    """
    today = today or dt.date.today()
    if end >= today:
        if (end - today).days > FORECAST_DAYS_AHEAD:
            raise NotAvailable(f"Forecasts only reach about {FORECAST_DAYS_AHEAD} days ahead.")
        url, source = FORECAST_URL, "Open-Meteo Forecast API"
    else:
        url, source = HISTORICAL_FORECAST_URL, "Open-Meteo Historical Forecast API"

    data = _get(url, _params(lat, lon, start, end))
    df = _to_frame(data)
    if df.empty:
        raise NotAvailable("No forecast data returned for those dates.")
    return {"source": source, "grid_point": _grid_point(data), "data": df}


def get_forecast_day(lat, lon, date, today=None):
    """Forecast for one date.

    Returns a dict: source, grid_point, date, and the three values (None if missing).
    """
    fc = get_forecast_range(lat, lon, date, date, today)
    row = fc["data"].iloc[0]
    values = {short: (None if pd.isna(row[short]) else float(row[short])) for short in VARIABLES.values()}
    return {"source": fc["source"], "grid_point": fc["grid_point"], "date": date, **values}


def _history_files(lat, lon):
    name = f"{lat:.2f}_{lon:.2f}"
    return HISTORY_DIR / f"{name}.csv", HISTORY_DIR / f"{name}.json"


def _fetch_history(lat, lon, start, end):
    params = _params(lat, lon, start, end)
    params["models"] = "era5"  # the whole record on the same ~25 km grid
    data = _get(ARCHIVE_URL, params)
    return _to_frame(data), _grid_point(data)


def get_history(lat, lon, start, end):
    """Daily ERA5 values from `start` to `end` (inclusive).

    Uses the saved file in data/history/ when it already covers the range and
    only downloads what is missing. The newest few days may not be in ERA5
    yet; those days are simply absent (not guessed).

    Returns a dict: source, grid_point, start, end, missing (count per column),
    and data (a pandas DataFrame with one row per day).
    """
    csv_path, meta_path = _history_files(lat, lon)
    saved, grid = None, None
    if csv_path.exists() and meta_path.exists():
        saved = pd.read_csv(csv_path, parse_dates=["date"])
        grid = json.loads(meta_path.read_text())["grid_point"]

    if saved is None or saved.empty or saved["date"].min().date() > start:
        fetched, grid = _fetch_history(lat, lon, start, end)
        saved = fetched
    elif saved["date"].max().date() < end:
        fetch_from = saved["date"].max().date() + dt.timedelta(days=1)
        fetched, _ = _fetch_history(lat, lon, fetch_from, end)
        saved = pd.concat([saved, fetched], ignore_index=True)
    else:
        fetched = None

    if fetched is not None:
        # Don't save trailing days ERA5 hasn't filled in yet; they get
        # downloaded again next time.
        has_value = saved[list(VARIABLES.values())].notna().any(axis=1)
        if has_value.any():
            saved = saved.loc[: has_value[has_value].index[-1]]
            HISTORY_DIR.mkdir(parents=True, exist_ok=True)
            saved.to_csv(csv_path, index=False, float_format="%.2f")
            meta_path.write_text(json.dumps({"source": HISTORY_SOURCE, "grid_point": grid}, indent=1))

    df = saved[(saved["date"].dt.date >= start) & (saved["date"].dt.date <= end)].reset_index(drop=True)
    return {
        "source": HISTORY_SOURCE,
        "grid_point": grid,
        "start": start,
        "end": end,
        "missing": {col: int(df[col].isna().sum()) for col in VARIABLES.values()},
        "data": df,
    }
