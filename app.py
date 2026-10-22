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

SUBTITLE = ("How unusual is today's weather for this place, compared with how it used to be, "
            "and what does it mean?")
TEMPLATE_FAILED = "Template mode: Claude's text didn't pass the checks."
TEMPLATE_UNREACHED = "Template mode: Claude couldn't be reached."
# claude_text.write() reasons that mean Claude never answered (anything else: its text didn't pass the checks).
UNREACHED = ("Claude took too long", "Claude couldn't be reached", "Claude returned an error", "no Claude key",
             "something went wrong asking Claude")
ABOUT_LINES = [
    "Code computes every number and sets the level. Claude writes only the headline, and code checks it: if it "
    "changes the level, adds a number or plays the risk down, the page shows fixed template wording instead.",
    "The level is the worse of how rare the day is here and fixed danger lines, so it leans toward warning. "
    "Recent rain, cold and snow can only raise it.",
    "On Typical days Claude isn't asked: they get the same standard wording every time, so no AI wording can "
    "play the day down.",
    message.NO_COLD_SNOW_LINES,
]
# Level colours. Never green: a green box could read as "all fine".
LEVEL_STYLE = {
    "Typical": ("#3d5a80", "#ffffff"),
    "Elevated": ("#f2b01e", "#2b1d00"),
    "High": ("#c2410c", "#ffffff"),
    "Extreme": ("#9b1c1c", "#ffffff"),
    risk.NOT_ENOUGH: ("#5f6672", "#ffffff"),
}
# Open-Meteo (WMO) weather codes -> (day icon, night icon, words). The strip shows the most dangerous code in
# each 3 hours (weather.CODE_DANGER). Freezing codes get their own words, also shown in the cell (no hover on phones).
FREEZING = {48: "Freezing fog", 56: "Freezing drizzle", 57: "Freezing drizzle", 66: "Freezing rain",
            67: "Freezing rain"}
WEATHER_ICONS = [
    (0, "☀️", "🌙", "Clear"), (1, "🌤️", "🌙", "Mostly clear"), (2, "⛅", "☁️", "Partly cloudy"),
    (3, "☁️", "☁️", "Overcast"), (45, "🌫️", "🌫️", "Fog"), (55, "🌦️", "🌦️", "Drizzle"),
    (65, "🌧️", "🌧️", "Rain"), (77, "🌨️", "🌨️", "Snow"), (82, "🌧️", "🌧️", "Rain showers"),
    (86, "🌨️", "🌨️", "Snow showers"), (95, "⛈️", "⛈️", "Thunderstorm"), (99, "⛈️", "⛈️", "Thunderstorm with hail"),
]
STRIP_CAPTION = "Raw forecast, not checked by Groundtruth. No storm icon doesn't mean no storm."


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


@st.cache_data(ttl=3600, show_spinner=False)
def cached_hourly(lat, lon, date, hour):
    """`hour` (the current hour) only makes the strip move on as the day goes on."""
    return weather.get_hourly(lat, lon, date)


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


def template_caption(problems):
    last = problems[-1] if problems else ""
    return TEMPLATE_UNREACHED if last.startswith(UNREACHED) else TEMPLATE_FAILED


def plain(text):
    """Claude's text shown as written: no markdown formatting, no maths."""
    return re.sub(r"([\\`*_\[\]<>#$~|])", r"\\\1", text)


# ---- pieces of the screen -----------------------------------------------------

def level_box(result, place):
    level = result["level"]
    background, colour = LEVEL_STYLE[level]
    where = f"{place} · {message.day_text(result['date'])}"
    st.markdown(
        f'<div style="background:{background};color:{colour};padding:0.9rem 1.25rem;border-radius:0.5rem;'
        f'margin:0.5rem 0 1rem 0" role="status">'
        f'<div style="font-size:0.85rem;opacity:0.9">{html.escape(where)}</div>'
        f'<div style="font-size:2.2rem;font-weight:700;line-height:1.2">{html.escape(level)}</div>'
        f'<div style="font-size:0.95rem;opacity:0.95">{html.escape(message.level_line(result))}</div></div>',
        unsafe_allow_html=True,
    )


def weather_icon(code, is_day):
    if code in FREEZING:
        return "🧊", FREEZING[code] + " — roads may be icy"
    for top, day, night, words in WEATHER_ICONS:
        if code is not None and code <= top:
            return (day if is_day is not False else night), words
    return "·", "No weather code"


def hourly_strip(slots, title):
    """Every 3 hours: time, icon, feels-like temperature, and rain or snow when there is some."""
    cells, last_day = [], None
    for s in slots:
        icon, words = weather_icon(s["weather_code"], s["is_day"])
        weekday = f"{s['time']:%a}" if s["time"].date() != last_day else "&nbsp;"
        last_day = s["time"].date()
        if s["snow_cm"]:
            wet = f"❄ {max(s['snow_cm'], 0.1):.1f} cm"
        elif s["rain_mm"]:
            wet = f"💧 {max(s['rain_mm'], 0.1):.1f} mm"
        else:
            wet = "&nbsp;"
        icy = (f'<div class="gt-small gt-icy">{FREEZING[s["weather_code"]].replace("Freezing ", "Freezing<br>")}'
               '</div>') if s["weather_code"] in FREEZING else ""
        cells.append(
            f'<div class="gt-hour" title="{html.escape(words)}">'
            f'<div class="gt-small">{weekday}</div><div class="gt-small">{s["time"]:%H:%M}</div>'
            f'<div class="gt-icon" role="img" aria-label="{html.escape(words)}">{icon}</div>'
            f'<div><strong>{s["feels_like_c"]:.0f}°</strong></div><div class="gt-small">{wet}</div>{icy}</div>'
        )
    st.markdown(f"**{title}**")
    st.markdown(
        "<style>.gt-strip{display:flex;gap:0.45rem;overflow-x:auto;padding-bottom:0.4rem;"
        "-webkit-overflow-scrolling:touch}.gt-hour{flex:0 0 4.3rem;text-align:center;"
        "border:1px solid rgba(128,128,128,0.35);border-radius:0.5rem;padding:0.35rem 0.2rem}"
        ".gt-small{font-size:0.75rem;opacity:0.8;white-space:nowrap}.gt-icon{font-size:1.4rem;line-height:1.6}"
        ".gt-icy{font-weight:700;opacity:1}"
        f"</style><div class=\"gt-strip\">{''.join(cells)}</div>",
        unsafe_allow_html=True,
    )
    st.caption(STRIP_CAPTION)


LONGEST_BAR = 0.6  # the more frequent period's line, as a share of the track
OLDER_COLOUR = "#8a929c"


def rarity_lines(rows, accent):
    """Two plain rows: period, a thin line, the engine's words. No axes, grid or scale numbers.

    On phones each row is "period …… words" on one line, with the line under it.
    """
    out = [
        "<style>.gt-rows{margin-bottom:1rem}.gt-row{display:grid;grid-template-columns:8.5rem 3fr 2fr;"
        "gap:0.3rem 0.9rem;align-items:center;margin-bottom:0.6rem}.gt-track{height:0.55rem}"
        ".gt-bar{height:100%;border-radius:0.3rem}"
        "@media (max-width:600px){.gt-row{grid-template-columns:1fr auto;grid-template-areas:'label words' "
        "'track track'}.gt-label{grid-area:label}.gt-words{grid-area:words;text-align:right}"
        ".gt-track{grid-area:track}}</style><div class=\"gt-rows\">"
    ]
    for i, r in enumerate(rows):
        colour = accent if i == 0 else OLDER_COLOUR  # the first row is now
        width = r["width"] * LONGEST_BAR * 100
        if r["per_year"] > 0:
            width = max(width, 0.5)  # a tiny but real rate still shows
        out.append(
            f'<div class="gt-row"><div class="gt-label"><strong>{html.escape(r["label"])}</strong></div>'
            f'<div class="gt-track" aria-hidden="true"><div class="gt-bar" '
            f'style="width:{width:.1f}%;background:{colour}"></div></div>'
            f'<div class="gt-words">{html.escape(r["words"])}</div></div>'
        )
    out.append("</div>")
    st.markdown("".join(out), unsafe_allow_html=True)


def then_and_now(result):
    blocks = message.then_and_now(result)
    if not blocks:  # e.g. a Typical day where every check happens 5 or more times a year
        return
    st.subheader("Then and now")
    for block in blocks:
        st.caption(block["caption"])
        rarity_lines(block["rows"], LEVEL_STYLE[result["level"]][0])
        for line in (block["too_few"], block["rough"]):
            if line:
                st.markdown(line)
        for line in (block["danger_note"], block["rarer_now"]):
            if line:
                st.markdown(f"**{line}**")


def numbers_section(result):
    with st.expander("The numbers"):  # written by code, never by Claude
        st.markdown("\n".join(f"- {line}" for line in message.number_lines(result)))
        fc, hist = result.get("forecast_grid_point"), result.get("history_grid_point")
        if fc and hist:
            st.caption(
                f"Forecast: {result['forecast_source']} (grid point {fc['latitude']:.2f}, {fc['longitude']:.2f}). "
                f"History: {result['history_source']} (grid point {hist['latitude']:.2f}, "
                f"{hist['longitude']:.2f}). Compared with {result['baseline_label']}; the level uses "
                f"{result['recent_label']} ({result['recent_phrase']})."
            )


def how_sure_section():
    with st.expander("How sure are we"):
        st.markdown("\n".join(f"- {line}" for line in message.HOW_SURE_LINES))


def about_section():
    with st.expander("About this tool"):
        st.markdown("\n".join(f"- {line}" for line in ABOUT_LINES))


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


def show_assessment(result, place, replay_name=None, lat=None, lon=None):
    level_box(result, place)
    special = replays.SPECIAL_NOTES.get(replay_name)
    level = result["level"]
    raised = level in risk.LEVELS[1:]
    reply, problems = claude_reply(result, place, replay_name) if raised else (None, [])
    *lines, storm_line = message.summary_lines(result, special)  # written by code, never by Claude

    if raised:
        st.markdown(f"### {plain(reply['headline']) if reply is not None else message.template_headline(result)}")
    for line in lines:
        if line == message.ICE_SMS:
            st.warning(line, icon="🧊")  # the same yellow style as the storm line
        else:
            st.markdown(f"**{line}**" if line == message.GEOLOGICAL_NOTE else line)
    if raised and reply is None:
        st.caption(template_caption(problems))

    today = dt.date.today()
    if replay_name is None and result["date"] >= today:  # never on past dates or replays
        try:
            slots = cached_hourly(lat, lon, result["date"], dt.datetime.now().strftime("%Y-%m-%d %H"))
        except Exception:  # no strip rather than an error
            slots = []
        if slots:
            title = "Next 48 hours" if result["date"] == today else f"{message.day_text(result['date'])}, hour by hour"
            hourly_strip(slots, title)

    then_and_now(result)
    st.warning(storm_line, icon="⚡")

    numbers_section(result)
    how_sure_section()
    about_section()


# ---- the page -----------------------------------------------------------------

st.set_page_config(page_title="Groundtruth", page_icon="🌍")
st.title("Groundtruth")
st.write(SUBTITLE)

replay_cases = {c["name"]: c for c in load_replays()}
today = dt.date.today()
st.session_state.setdefault("date", today)
st.session_state.setdefault("replay", NO_REPLAY)


def replay_picked():
    """A replay fills the place and date fields; "none" clears the place."""
    name = st.session_state.replay
    if name == NO_REPLAY:
        st.session_state.query = ""
        return
    case = replay_cases[name]
    st.session_state.query = replays.place_of(case)
    st.session_state.date = dt.date.fromisoformat(case["date"])


def place_or_date_changed():
    """Changing the place or the date switches the replay off."""
    st.session_state.replay = NO_REPLAY


replaying = st.session_state.replay != NO_REPLAY
query = st.text_input("Search for a place", placeholder="e.g. Kolkata", key="query", on_change=place_or_date_changed)
picked, search_problem = None, None
if query.strip() and not replaying:  # a replay never searches
    try:
        matches = cached_search(query.strip())
    except (weather.LimitReached, requests.RequestException):
        search_problem = LIVE_DOWN
    except weather.NotAvailable:
        search_problem = "Couldn't search for that place. Try a replay."
    else:
        if not matches:
            search_problem = "No place found with that name. Try another spelling."
        else:
            labels = [m["label"] for m in matches]
            choice = st.selectbox("Which place?", labels)
            picked = matches[labels.index(choice)]
date = st.date_input("Date", key="date", min_value=EARLIEST_DATE, on_change=place_or_date_changed,
                     max_value=today + dt.timedelta(days=weather.FORECAST_DAYS_AHEAD))
replay_name = st.columns([2, 3])[0].selectbox("Or replay a past event", [NO_REPLAY, *replay_cases], key="replay",
                                              on_change=replay_picked)

lat = lon = place = None
problem = None

if replay_name != NO_REPLAY:
    case = replay_cases[replay_name]
    lat, lon = float(case["latitude"]), float(case["longitude"])
    date = dt.date.fromisoformat(case["date"])
    place = replays.place_of(case)
elif picked is not None:
    lat, lon, place = picked["latitude"], picked["longitude"], picked["label"]
else:
    problem = search_problem or "Search for a place above, or pick a replay."

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
    show_assessment(result, place, None if replay_name == NO_REPLAY else replay_name, lat, lon)

st.divider()
phase2_cards()
st.divider()
st.caption("Weather data by Open-Meteo.com")
