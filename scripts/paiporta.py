"""Print the forecast and the history (1951 to the day before) for Paiporta, Spain, on 2024-10-29.

Run from the project folder:  python scripts/paiporta.py
"""

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from groundtruth.weather import get_forecast_day, get_history  # noqa: E402

LAT, LON = 39.43, -0.42
DATE = dt.date(2024, 10, 29)

LABELS = {
    "rain_mm": ("Rain (daily total)", "mm"),
    "feels_like_max_c": ("Feels-like max", "°C"),
    "gust_max_kmh": ("Wind gust max", "km/h"),
}


def fmt(value, unit):
    return "missing" if value is None else f"{value:.1f} {unit}"


def main():
    print(f"Paiporta, Spain ({LAT}, {LON}) on {DATE}\n")

    fc = get_forecast_day(LAT, LON, DATE)
    hist = get_history(LAT, LON, dt.date(1951, 1, 1), DATE - dt.timedelta(days=1))
    df = hist["data"]

    print("Grid points (the data's nearest model cell, not the exact address):")
    print(f"  Forecast: {fc['grid_point']['latitude']:.3f}, {fc['grid_point']['longitude']:.3f}")
    print(f"  History:  {hist['grid_point']['latitude']:.3f}, {hist['grid_point']['longitude']:.3f}\n")

    print(f"Forecast for {DATE} — {fc['source']}")
    for key, (label, unit) in LABELS.items():
        print(f"  {label:<20} {fmt(fc[key], unit)}")

    print(f"\nHistory {hist['start']} to {hist['end']} — {hist['source']}")
    print(f"  Days: {len(df)}")
    for key, (label, unit) in LABELS.items():
        col = df[key]
        print(f"  {label}:")
        print(f"    missing days   {hist['missing'][key]}")
        if col.notna().any():
            top = df.loc[col.idxmax()]
            print(f"    typical day    {fmt(col.median(), unit)} (median)")
            print(f"    highest ever   {fmt(top[key], unit)} on {top['date'].date()}")

    print("\nWeather data by Open-Meteo.com")


if __name__ == "__main__":
    main()
