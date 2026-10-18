"""Groundtruth — how unusual is the weather for this exact place, and what does it mean?

Run:  streamlit run app.py
"""

import datetime as dt
import html
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from groundtruth import geocode, message, risk, weather

ROOT = Path(__file__).resolve().parent
CASES_FILE = ROOT / "tests" / "cases.csv"

EARLIEST_DATE = dt.date(2017, 1, 1)  # the past-forecast archive goes back about this far
NO_REPLAY = "— none, use the search above —"
LIVE_DOWN = "Live data is temporarily unavailable. Try a replay."

# Test cases that are not offered as replays.
HIDDEN_REPLAY_PREFIX = "Ordinary rain"
# Replays that get the geological-hazards warning right under the level.
GEOLOGICAL_REPLAYS = {"Nepal-Tibet glacier-collapse flood"}

REPLAY_PLACES = {
    "Valencia flash flood": "Paiporta, Valencia, Spain",
    "Texas Hill Country flood": "Texas Hill Country, USA",
    "Kolkata heat (KK concert)": "Kolkata, India",
    "Bayesian sinking": "Porticello, Sicily, Italy",
    "Nepal-Tibet glacier-collapse flood": "Nepal–Tibet border area",
    "Calm control 1, Paiporta": "Paiporta, Valencia, Spain",
    "Calm control 2, Kolkata": "Kolkata, India",
}

GEOLOGICAL_NOTE = (
    "Groundtruth covers weather-driven hazards only. For geological hazards (landslides, "
    "glacier collapse, earthquakes), check local civil protection and geological authorities."
)
# Level colours. Never green: a green box could read as "all fine".
LEVEL_STYLE = {
    "Typical": ("#3d5a80", "#ffffff"),
    "Elevated": ("#f2b01e", "#2b1d00"),
    "High": ("#c2410c", "#ffffff"),
    "Extreme": ("#9b1c1c", "#ffffff"),
    risk.NOT_ENOUGH: ("#5f6672", "#ffffff"),
}


# ---- data (cached) ----------------------------------------------------------

@st.cache_data
def load_replays():
    cases = pd.read_csv(CASES_FILE, dtype=str)
    cases = cases[~cases["name"].str.startswith(HIDDEN_REPLAY_PREFIX)]
    return cases.to_dict("records")


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def cached_search(query):
    return geocode.search_places(query)


@st.cache_data(ttl=3600, show_spinner=False)
def cached_live(lat, lon, date):
    return risk.assess(lat, lon, date)


@st.cache_data(show_spinner=False)
def cached_replay(lat, lon, date):
    with weather.offline():  # a replay never calls Open-Meteo
        return risk.assess(lat, lon, date)


# ---- pieces of the screen -----------------------------------------------------

def level_banner(result):
    level = result["level"]
    background, colour = LEVEL_STYLE[level]
    deciders = ", ".join(result.get("decided_by") or [])
    note = f"Set by: {html.escape(deciders)}" if deciders else "Not enough data — check official sources"
    st.markdown(
        f'<div style="background:{background};color:{colour};padding:1rem 1.25rem;border-radius:0.5rem;'
        f'margin:0.5rem 0 1rem 0" role="status">'
        f'<div style="font-size:0.85rem;letter-spacing:0.05em;text-transform:uppercase;opacity:0.9">Level</div>'
        f'<div style="font-size:2.2rem;font-weight:700;line-height:1.2">{html.escape(level)}</div>'
        f'<div style="font-size:0.95rem;opacity:0.95">{note}</div></div>',
        unsafe_allow_html=True,
    )


def how_sure_box(result):
    rain = result["checks"][-1]
    with st.container(border=True):
        st.subheader("How sure are we")
        st.markdown(
            "- Official weather warnings come first. Groundtruth never replaces them.\n"
            "- The history data is a grid of about 25 km, so it misses very local storms.\n"
            f"- {GEOLOGICAL_NOTE}"
        )
        if rain.get("source") == "forecast":
            st.markdown("- The rain totals assume the forecast rain actually falls.")
        with st.expander("Details"):
            st.markdown(
                f"- Forecast: {result['forecast_source']} (grid point "
                f"{result['forecast_grid_point']['latitude']:.2f}, {result['forecast_grid_point']['longitude']:.2f})\n"
                f"- History: {result['history_source']} (grid point "
                f"{result['history_grid_point']['latitude']:.2f}, {result['history_grid_point']['longitude']:.2f})\n"
                f"- Compared with {result['baseline_label']}; the level uses {result['recent_label']} "
                f"({result['recent_phrase']})"
            )
            engine_notes = result["notes"][: len(result["notes"]) - len(risk.ALWAYS_NOTES)]
            engine_notes += [f"{c['name']}: {n}" for c in result["checks"] for n in c["notes"]]
            for n in engine_notes:
                st.markdown(f"- {n}")


def phase2_cards():
    cols = st.columns(2)
    cards = [("Layer 2 — Infrastructure", "Roads, bridges, drainage and power in the affected area."),
             ("Layer 3 — Response history", "How past events here were handled, and what helped.")]
    for col, (title, text) in zip(cols, cards):
        col.markdown(
            '<div aria-disabled="true" style="opacity:0.45;border:1px dashed currentColor;border-radius:0.5rem;'
            f'padding:0.9rem 1rem"><strong>{title}</strong> '
            '<span style="font-size:0.75rem;border:1px solid currentColor;border-radius:1rem;padding:0 0.5rem;'
            f'margin-left:0.4rem">Phase 2</span><br><span style="font-size:0.9rem">{text}</span></div>',
            unsafe_allow_html=True,
        )


def show_assessment(result, place, replay_name=None):
    level_banner(result)
    if replay_name in GEOLOGICAL_REPLAYS:
        st.warning(f"**Weather data can't see everything.** {GEOLOGICAL_NOTE}", icon="⚠️")

    st.markdown(f"**{place} — {message.day_text(result['date'])}**")
    st.markdown(f"### {message.template_sentence(result)}")
    st.caption("Template mode: this sentence is built from the numbers, not written by an AI.")

    st.subheader("Why")
    st.markdown("\n".join(f"- {b}" for b in message.why_bullets(result)))

    chart = message.chart_frame(result)
    if chart is not None:
        frame, check_name = chart
        st.subheader("How often a day like this happens")
        if (frame["Times a year"] == 0).all():
            st.markdown(f"**{check_name}:** a day like this was not seen in {result['baseline_label']} "
                        f"or in {result['recent_label']}.")
        else:
            st.bar_chart(frame, y="Times a year")
            st.caption(f"{check_name}: days at or beyond this value, per year, in "
                       f"{result['baseline_label']} and in {result['recent_label']}.")

    st.subheader("Text message version")
    sms = message.sms_text(result, place)
    st.code(sms, language=None, wrap_lines=True)
    st.caption(f"{len(sms)} of 160 characters")

    how_sure_box(result)


# ---- the page -----------------------------------------------------------------

st.set_page_config(page_title="Groundtruth", page_icon="🌍")
st.title("Groundtruth")
st.write("How unusual is today's weather for your exact place, compared with how it used to be, and what does it mean?")

replays = {c["name"]: c for c in load_replays()}
today = dt.date.today()

query = st.text_input("Search for a place", placeholder="e.g. Valencia")
date = st.date_input("Date", value=today, min_value=EARLIEST_DATE, max_value=today + dt.timedelta(days=weather.FORECAST_DAYS_AHEAD))
replay_name = st.selectbox("Replay a past event", [NO_REPLAY, *replays])

lat = lon = place = None
problem = None

if replay_name != NO_REPLAY:
    case = replays[replay_name]
    lat, lon = float(case["latitude"]), float(case["longitude"])
    date = dt.date.fromisoformat(case["date"])
    place = REPLAY_PLACES.get(replay_name, f"{lat:.2f}, {lon:.2f}")
    st.caption("Replay: saved data, no live lookup. The place and date above are ignored.")
elif query.strip():
    try:
        matches = cached_search(query.strip())
    except (weather.LimitReached, requests.RequestException):
        problem = LIVE_DOWN
    except weather.NotAvailable:
        problem = "Couldn't search for that place. Try a replay."
    else:
        if not matches:
            problem = "No place found with that name. Try another spelling."
        else:
            labels = [m["label"] for m in matches]
            choice = st.selectbox("Which place?", labels) if len(matches) > 1 else labels[0]
            picked = matches[labels.index(choice)]
            lat, lon, place = picked["latitude"], picked["longitude"], choice
else:
    problem = "Search for a place above, or pick a replay."

result = None
if lat is not None:
    try:
        with st.spinner("Checking the weather record…"):
            if replay_name != NO_REPLAY:
                result = cached_replay(lat, lon, date)
            else:
                result = cached_live(lat, lon, date)
    except (weather.LimitReached, requests.RequestException):
        problem = LIVE_DOWN
    except weather.NotAvailable as e:
        if replay_name != NO_REPLAY:
            problem = "This replay's saved data is missing. Ask for it to be saved again."
        else:
            problem = f"No weather data for that place and date ({e}). Try another date, or a replay."

if problem:
    (st.info if problem != LIVE_DOWN else st.warning)(problem)
if result is not None:
    st.divider()
    show_assessment(result, place, None if replay_name == NO_REPLAY else replay_name)

st.divider()
phase2_cards()
st.divider()
st.caption("Weather data by Open-Meteo.com")
