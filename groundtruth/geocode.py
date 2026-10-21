"""Place search using the Open-Meteo geocoding service (no API key needed)."""

from groundtruth.weather import _get

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def search_places(query, count=10):
    """Places matching `query`, most populated first. Each is a dict: label ("Kolkata, West Bengal, India"),
    latitude, longitude.

    Raises LimitReached / requests errors if Open-Meteo refuses. Returns [] if nothing matches.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []
    data = _get(GEOCODING_URL, {"name": query, "count": count, "language": "en", "format": "json"})
    places = []
    results = sorted(data.get("results") or [], key=lambda r: -(r.get("population") or 0))  # sorted() is stable
    for r in results:
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        label = ", ".join(dict.fromkeys(p for p in parts if p))  # no repeats like "Valencia, Valencia"
        places.append({"label": label, "latitude": r["latitude"], "longitude": r["longitude"]})
    return places
