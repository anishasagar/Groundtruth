"""Download and save everything the replays need, so they work without Open-Meteo.

Run from the project folder:  python scripts/save_replay_data.py

Safe to run again: anything already saved is skipped. Order (most important first,
in case Open-Meteo's daily limit runs out partway):
  1. the forecast for each test case (daily values, plus hourly weather code and
     CAPE — saved for later, not used by the app yet)
  2. new history columns for places already saved (existing values are kept)
  3. full history for new places
  4. picks the "Ordinary snow, Montreal" test day, if it isn't in tests/cases.csv yet
Then run:  python scripts/replay.py
"""

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import risk, weather  # noqa: E402

CASES = ROOT / "tests" / "cases.csv"
HOURLY = ("weather_code", "cape")
STORM_CODES = {95, 96, 99}  # thunderstorm, with slight / heavy hail

MONTREAL = (45.50, -73.57)
MONTREAL_NAME = "Ordinary snow, Montreal"
MONTREAL_MIN_CM = 2.0  # clearly a snowy day, not a trace
MONTREAL_MIN_PER_YEAR = 3  # that much snow happens at least this often in the recent window


def _forecast_saved(lat, lon, date):
    path = weather._forecast_file(lat, lon, date, date)
    if not path.exists() or weather._load_saved_forecast(lat, lon, date, date) is None:
        return False
    return all(h in (json.loads(path.read_text())["raw"].get("hourly") or {}) for h in HOURLY)


def save_forecast(name, lat, lon, date):
    if _forecast_saved(lat, lon, date):
        print(f"  forecast already saved: {name} {date}")
        return
    path = weather.save_forecast_range(lat, lon, date, date, hourly=HOURLY)
    print(f"  forecast saved: {name} {date} -> {path.name}")


def history_start(date):
    return dt.date(min(risk.BASELINE_START_YEAR, risk.recent_window(date)[0].year), 1, 1)


def save_history(lat, lon, dates):
    """History from 1951 to the day before the latest case date at this place."""
    last = max(dates)
    weather.get_history(lat, lon, history_start(min(dates)), last - dt.timedelta(days=1))
    print(f"  history saved: {lat:.2f}, {lon:.2f} up to {last - dt.timedelta(days=1)}")


def pick_montreal_day(cases):
    """An ordinary snowy day in Montreal (2017 or later) where that much snow happens >= 3 times a year."""
    if (cases["name"] == MONTREAL_NAME).any():
        print("  Montreal day already chosen")
        return cases
    lat, lon = MONTREAL
    hist = weather.get_history(lat, lon, dt.date(risk.BASELINE_START_YEAR, 1, 1), dt.date(2025, 12, 31))["data"]
    winter = hist[(hist["date"].dt.year >= 2017) & (hist["date"].dt.month.isin([12, 1, 2]))
                  & (hist["snow_cm"] >= MONTREAL_MIN_CM)]

    def per_year(values, threshold, date, lower=False):
        start, end = risk.recent_window(date)
        r = risk._rarity(hist["date"], values, threshold, start, end, risk.RECENT_WINDOW_YEARS, lower=lower)
        return r["per_year"] if r else 0

    candidates = []
    for _, row in winter.iterrows():
        date = row["date"].date()
        snow_rate = per_year(hist["snow_cm"], row["snow_cm"], date)
        cold_rate = per_year(hist["feels_like_min_c"], row["feels_like_min_c"], date, lower=True)
        if snow_rate >= MONTREAL_MIN_PER_YEAR + 1 and cold_rate >= 2:  # a margin, as the forecast may differ
            candidates.append((row["snow_cm"], date, snow_rate, cold_rate))
    candidates.sort(reverse=True)  # the snowiest day that is still ordinary for Montreal

    for era5_snow, date, era5_rate, cold_rate in candidates[:5]:
        save_forecast("Montreal candidate", lat, lon, date)
        fc = weather.get_forecast_day(lat, lon, date)
        if fc["snow_cm"] is None:
            continue
        fc_rate = per_year(hist["snow_cm"], fc["snow_cm"], date)
        print(f"  candidate {date}: ERA5 snow {era5_snow:.1f} cm ({era5_rate:.1f}/yr), forecast snow "
              f"{fc['snow_cm']:.1f} cm ({fc_rate:.1f}/yr), cold this low {cold_rate:.1f}/yr")
        if fc_rate < MONTREAL_MIN_PER_YEAR:
            weather._forecast_file(lat, lon, date, date).unlink()  # not picked: don't keep its file
        else:
            expect = (f"Ordinary snowy day (forecast {fc['snow_cm']:.1f} cm; that much or more happens about "
                      f"{fc_rate:.0f} times a year here): Typical")
            row = {"name": MONTREAL_NAME, "latitude": f"{lat:.2f}", "longitude": f"{lon:.2f}",
                   "date": date.isoformat(), "expect": expect, "lowest_expected": "Typical",
                   "highest_expected": "Typical"}
            cases = pd.concat([cases, pd.DataFrame([row])], ignore_index=True)
            cases.to_csv(CASES, index=False)
            print(f"  picked Montreal {date}")
            return cases
    print("  no Montreal day found that meets the rule")
    return cases


def storm_report(cases):
    """Thunderstorm codes and highest CAPE in each saved forecast (report only; the app doesn't use them)."""
    print("\nStorm signals in the saved forecasts (report only):")
    for _, case in cases.iterrows():
        date = dt.date.fromisoformat(case["date"])
        path = weather._forecast_file(float(case["latitude"]), float(case["longitude"]), date, date)
        if not path.exists():
            continue
        hourly = json.loads(path.read_text())["raw"].get("hourly") or {}
        codes = [c for c in hourly.get("weather_code", []) if c is not None]
        cape = [c for c in hourly.get("cape", []) if c is not None]
        storm_hours = sum(c in STORM_CODES for c in codes)
        found = sorted(set(c for c in codes if c in STORM_CODES)) or "none"
        top_cape = f"{max(cape):.0f} J/kg" if cape else "not saved"
        print(f"  {case['name']} {case['date']}: thunderstorm hours {storm_hours} (codes {found}), "
              f"highest CAPE {top_cape}")


def main():
    cases = pd.read_csv(CASES, dtype=str)
    try:
        print("1. Forecasts")
        for _, c in cases.iterrows():
            save_forecast(c["name"], float(c["latitude"]), float(c["longitude"]), dt.date.fromisoformat(c["date"]))
        print("2-3. History")
        places = cases.groupby(["latitude", "longitude"])["date"].apply(list)
        for (lat, lon), dates in places.items():
            save_history(float(lat), float(lon), [dt.date.fromisoformat(d) for d in dates])
        print("4. Montreal")
        cases = pick_montreal_day(cases)
    except weather.LimitReached as e:
        print(f"\nStopped: {e} Run this again later; it continues where it stopped.")
        sys.exit(2)
    storm_report(cases)
    print("\nDone. Now run: python scripts/replay.py")


if __name__ == "__main__":
    main()
