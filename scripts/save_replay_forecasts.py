"""Save the forecast for every test case in data/forecasts/, so replays work without Open-Meteo.

Run from the project folder:  python scripts/save_replay_forecasts.py
Needs Open-Meteo to be reachable (it makes one request per case). Run it again after
adding a case to tests/cases.csv.
"""

import datetime as dt
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import weather  # noqa: E402


def main():
    cases = pd.read_csv(ROOT / "tests" / "cases.csv", dtype=str)
    for _, case in cases.iterrows():
        lat, lon = float(case["latitude"]), float(case["longitude"])
        date = dt.date.fromisoformat(case["date"])
        path = weather.save_forecast_range(lat, lon, date, date)
        print(f"{case['name']} ({case['date']}) -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
