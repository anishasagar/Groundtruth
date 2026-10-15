"""Fetch weather numbers from Open-Meteo (no API key needed).

Two things:
- get_forecast_day: the forecast for one date (rain, max feels-like, max gust).
- get_history: the same three values for every day from 1951 to the year
  before that date, from the ERA5 reanalysis (~25 km grid).

Missing values stay missing (None / NaN). Nothing is filled in or guessed.
"""

import datetime as dt
import time

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

HISTORY_START_YEAR = 1951
FORECAST_DAYS_AHEAD = 16  # the Forecast API reaches about this far


class NotAvailable(Exception):
    """The requested data does not exist (date out of range, etc.)."""


def _get(url, params, tries=4):
    """GET with a few retries on network errors. Raises if it still fails."""
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, timeout=60)
        except requests.RequestException:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)
            continue
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


def get_forecast_day(lat, lon, date, today=None):
    """Forecast for one date.

    Today or future -> Forecast API.
    Past -> Historical Forecast API. Note: that archive stitches together the
    *most recent* model run for each hour, so it shows what models predicted a
    few hours ahead, not what a forecast issued days earlier said.

    Returns a dict: source, grid_point, date, and the three values (None if missing).
    Raises NotAvailable if the date is outside what the source covers.
    """
    today = today or dt.date.today()
    if date >= today:
        if (date - today).days > FORECAST_DAYS_AHEAD:
            raise NotAvailable(f"Forecasts only reach about {FORECAST_DAYS_AHEAD} days ahead.")
        url, source = FORECAST_URL, "Open-Meteo Forecast API"
    else:
        url, source = HISTORICAL_FORECAST_URL, "Open-Meteo Historical Forecast API"

    data = _get(url, _params(lat, lon, date, date))
    df = _to_frame(data)
    if df.empty:
        raise NotAvailable("No forecast data returned for that date.")
    row = df.iloc[0]
    values = {short: (None if pd.isna(row[short]) else float(row[short])) for short in VARIABLES.values()}
    return {"source": source, "grid_point": _grid_point(data), "date": date, **values}


def get_history(lat, lon, date):
    """Daily values from 1 Jan 1951 to 31 Dec of the year before `date`.

    Uses ERA5 only (models=era5) so the whole record is on the same ~25 km grid.

    Returns a dict: source, grid_point, start, end, missing (count per column),
    and data (a pandas DataFrame with one row per day).
    """
    start = dt.date(HISTORY_START_YEAR, 1, 1)
    end = dt.date(date.year - 1, 12, 31)
    if end < start:
        raise NotAvailable("No history before 1951.")

    params = _params(lat, lon, start, end)
    params["models"] = "era5"
    data = _get(ARCHIVE_URL, params)
    df = _to_frame(data)
    return {
        "source": "Open-Meteo Historical Weather API (ERA5)",
        "grid_point": _grid_point(data),
        "start": start,
        "end": end,
        "missing": {col: int(df[col].isna().sum()) for col in VARIABLES.values()},
        "data": df,
    }
