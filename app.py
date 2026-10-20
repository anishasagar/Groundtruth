"""Groundtruth — how unusual is the weather for this exact place, and what does it mean?

Run:  streamlit run app.py
"""

import datetime as dt
import html
import os
import re

import requests
import streamlit as st

from groundtruth import claude_text, geocode, message, replays, risk, weather

EARLIEST_DATE = dt.date(2017, 1, 1)  # the past-forecast archive goes back about this far
NO_REPLAY = "— none, use the search above —"
LIVE_DOWN = "Live data is temporarily unavailable. Try a replay."
REPLAY_MISSING = "Replay data for this event isn't saved yet. Please try again later."

# Replays that get the geological-hazards warning right under the level.
GEOLOGICAL_REPLAYS = {name for name, note in replays.SPECIAL_NOTES.items() if note == "geological"}
GEOLOGICAL_NOTE = message.GEOLOGICAL_NOTE
TYPICAL_CAPTION = ("On Typical days this text is fixed wording, reviewed in advance; "
                   "Claude only writes on raised days.")
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
    return replays.load_replays()


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


def claude_key():
    """From st.secrets, else the environment. Never shown or saved."""
    try:
        key = st.secrets.get("GROUNDTRUTH_CLAUDE_KEY")
    except Exception:  # no secrets file
        key = None
    return key or os.environ.get("GROUNDTRUTH_CLAUDE_KEY")


def claude_live(facts):
    """Claude's reply for a live search, kept for this visitor so reruns don't ask again. Failures aren't kept."""
    kept = st.session_state.setdefault("claude_replies", {})
    fingerprint = claude_text.fingerprint(facts)
    if fingerprint in kept:
        return kept[fingerprint], []
    reply, problems = claude_text.write(facts, claude_text.make_client(claude_key()))
    if reply is not None:
        kept[fingerprint] = reply
    return reply, problems


def claude_reply(result, place, replay_name):
    """(reply, problems). A replay only uses its saved reply; it never calls Claude."""
    facts = claude_text.facts(result, place, dt.date.today(), replays.SPECIAL_NOTES.get(replay_name))
    if replay_name is not None:
        return claude_text.saved_reply(replays.claude_reply_file(replay_name), facts)
    if result["level"] not in risk.LEVELS:
        return claude_text.write(facts, None)  # "Not enough data" never goes to Claude
    with st.spinner("Writing the summary…"):
        return claude_live(facts)


def plain(text):
    """Claude's text shown as written: no markdown formatting, no maths."""
    return re.sub(r"([\\`*_\[\]<>#$~|])", r"\\\1", text)


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


LONGEST_BAR = 0.6  # the more frequent period's line, as a share of the track
OLDER_COLOUR = "#8a929c"


def rarity_lines(rows, accent):
    """Two plain rows: period, a thin line, the engine's words. No axes, grid or scale numbers."""
    out = [
        "<style>.gt-rows{display:grid;grid-template-columns:5.5rem 3fr 2fr;gap:0.6rem 0.9rem;align-items:center}"
        ".gt-track{height:0.55rem}.gt-bar{height:100%;border-radius:0.3rem}"
        "@media (max-width:600px){.gt-rows{grid-template-columns:5rem 1fr}.gt-words{grid-column:2}"
        ".gt-label{grid-row-start:auto}}</style><div class=\"gt-rows\">"
    ]
    for i, r in enumerate(rows):
        colour = accent if i == len(rows) - 1 else OLDER_COLOUR  # the last row is the recent period
        width = r["width"] * LONGEST_BAR * 100
        if r["per_year"] > 0:
            width = max(width, 0.5)  # a tiny but real rate still shows
        out.append(
            f'<div class="gt-label"><strong>{html.escape(r["label"])}</strong></div>'
            f'<div class="gt-track" aria-hidden="true"><div class="gt-bar" '
            f'style="width:{width:.1f}%;background:{colour}"></div></div>'
            f'<div class="gt-words">{html.escape(r["words"])}</div>'
        )
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def how_sure_box(result, confidence_note=None):
    rain = result["checks"][-1]
    with st.container(border=True):
        st.subheader("How sure are we")
        if confidence_note:
            st.markdown(f"**In short (written by Claude):** {plain(confidence_note)}")
        st.warning(message.STORM_NOTE, icon="⚡")
        st.markdown(message.SCOPE_LINE)
        st.markdown(
            "- Official weather warnings come first. Groundtruth never replaces them.\n"
            "- The history data is a grid of about 25 km, so it misses very local storms.\n"
            f"- {message.FORECAST_NOTE}\n"
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
            st.markdown(f"- Rain in the {risk.RECENT_RAIN_DAYS_BEFORE} days before: from {rain['source']}")
            st.markdown("- There are no fixed danger lines for cold or snow yet; fixed cold lines need research. "
                        "Those two checks use only how rare the day is here.")
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
    special = replays.SPECIAL_NOTES.get(replay_name)
    typical = result["level"] == "Typical"
    reply, problems = (None, []) if typical else claude_reply(result, place, replay_name)
    ice = message.ice_line(result)  # shown right under the headline in every mode
    if typical:  # fixed wording; Claude is never asked on Typical days
        st.markdown(f"### {message.HEADLINES['Typical']}")
        if ice:
            st.markdown(f"**{ice}**")
        st.markdown(message.what_it_means(result, special))
        st.caption(TYPICAL_CAPTION)
    elif reply is not None:
        st.markdown(f"### {plain(reply['headline'])}")
        if ice:
            st.markdown(f"**{ice}**")
        st.markdown(message.what_it_means(result, special))  # written by code, never by Claude
        st.markdown("\n".join(f"- {plain(b)}" for b in reply["why"]))
        st.caption("Written by Claude from the computed facts. The level is set in code, "
                   "and every number appears in those facts.")
    else:
        st.markdown(f"### {message.template_sentence(result)}")
        if ice:
            st.markdown(f"**{ice}**")
        st.caption("Template mode: this sentence is built from the numbers, not written by an AI.  \n"
                   f"Claude's text wasn't used: {plain(claude_text.short_reason(problems))}.")
    st.warning(message.STORM_NOTE, icon="⚡")

    st.subheader("The numbers")
    st.markdown("\n".join(f"- {b}" for b in message.why_bullets(result)))

    rarity = message.rarity_rows(result)
    if rarity is not None:
        rows, check_name, like_this = rarity
        st.subheader("How often a day like this happens")
        if all(r["per_year"] == 0 for r in rows):
            st.markdown(f"**{check_name}:** a day like this was not seen in {result['baseline_label']} "
                        f"or in {result['recent_label']}.")
        else:
            rarity_lines(rows, LEVEL_STYLE[result["level"]][0])
            st.caption(f"{check_name}: {like_this}. The longer line is the period with more of them.")

    st.subheader("Text message version")
    sms = message.sms_text(result, place, special)  # written by code, never by Claude
    st.code(sms, language=None, wrap_lines=True)
    st.caption(f"{len(sms)} of 160 characters")

    how_sure_box(result, reply["confidence_note"] if reply is not None else None)


# ---- the page -----------------------------------------------------------------

st.set_page_config(page_title="Groundtruth", page_icon="🌍")
st.title("Groundtruth")
st.write("How unusual is today's weather for your exact place, compared with how it used to be, and what does it mean?")

replay_cases = {c["name"]: c for c in load_replays()}
today = dt.date.today()

query = st.text_input("Search for a place", placeholder="e.g. Valencia")
date = st.date_input("Date", value=today, min_value=EARLIEST_DATE, max_value=today + dt.timedelta(days=weather.FORECAST_DAYS_AHEAD))
replay_name = st.selectbox("Replay a past event", [NO_REPLAY, *replay_cases])

lat = lon = place = None
problem = None

if replay_name != NO_REPLAY:
    case = replay_cases[replay_name]
    lat, lon = float(case["latitude"]), float(case["longitude"])
    date = dt.date.fromisoformat(case["date"])
    place = replays.place_of(case)
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
            problem = REPLAY_MISSING
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
