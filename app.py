"""Groundtruth — how unusual is the weather for this exact place, and what does it mean?

Run:  streamlit run app.py
"""

import datetime as dt
import html

import requests
import streamlit as st

# Every word on the page is written by code. Claude (groundtruth/claude_text.py) is switched off and kept for
# Phase 2; any Claude text that comes back must be shown in purple, labelled "written by Claude" (CLAUDE.md rule 9).
from groundtruth import geocode, message, replays, risk, weather

EARLIEST_DATE = dt.date(2017, 1, 1)  # the past-forecast archive goes back about this far
NO_REPLAY = "— none, use the search above —"
LIVE_DOWN = "Live data is temporarily unavailable. Try a replay."
REPLAY_MISSING = "Replay data for this event isn't saved yet. Please try again later."

SUBTITLE = ("How unusual is today's weather for this place, compared with how it used to be, "
            "and what does it mean?")
ABOUT_LINES = [
    "Every sentence on this page is fixed wording written by code, from numbers computed by code.",
    "AI wording (Claude) was tested and switched off because it kept drifting towards reassurance.",
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
STRIP_CAPTION = "No storm icon doesn't mean no storm."


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
def cached_history(lat, lon, date, replay):
    """The history at this spot, for the hero line (already saved by risk.assess, so no new download)."""
    start, end = message.hero_history_range(date)
    if replay:
        with weather.offline():
            return weather.get_history(lat, lon, start, end)["data"]
    return weather.get_history(lat, lon, start, end)["data"]


@st.cache_data(ttl=3600, show_spinner=False)
def cached_hourly(lat, lon, date, hour):
    """`hour` (the current hour) only makes the strip move on as the day goes on."""
    return weather.get_hourly(lat, lon, date)


# ---- pieces of the screen -----------------------------------------------------

def level_box(result, place, hero=None):
    """Place · date, the level word, the hero line (raised days only, bold), then the value line (smaller)."""
    level = result["level"]
    background, colour = LEVEL_STYLE[level]
    where = f"{place} · {message.day_text(result['date'])}"
    hero_html = (f'<div style="font-size:1.15rem;font-weight:700;line-height:1.3;margin:0.15rem 0 0.2rem 0">'
                 f'{html.escape(hero)}</div>') if hero else ""
    st.markdown(
        f'<div style="background:{background};color:{colour};padding:0.9rem 1.25rem;border-radius:0.5rem;'
        f'margin:0.5rem 0 1rem 0" role="status">'
        f'<div style="font-size:0.85rem;opacity:0.9">{html.escape(where)}</div>'
        f'<div style="font-size:2.2rem;font-weight:700;line-height:1.2">{html.escape(level)}</div>{hero_html}'
        f'<div style="font-size:0.85rem;opacity:0.95">{html.escape(message.level_line(result))}</div></div>',
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


LONGEST_BAR = 0.9  # the most frequent row in the whole section, as a share of the width
OLDER_COLOUR = "#8a929c"
# Card backgrounds: a light tint of the check's level colour; Typical cards neutral grey.
CARD_TINT = {"Elevated": "rgba(242,176,30,0.16)", "High": "rgba(194,65,12,0.12)",
             "Extreme": "rgba(155,28,28,0.14)", "Typical": "rgba(128,128,128,0.10)"}


def card_rows(rows, accent):
    """Two rows: period and its words on one line, a thin rounded bar under it (no track, no axes).

    Widths share one scale across the whole section (message.then_and_now)."""
    out = ['<div class="gt-rows">']
    for i, r in enumerate(rows):
        colour = accent if i == 0 else OLDER_COLOUR  # the first row is now
        width = r["width"] * LONGEST_BAR * 100
        if r["per_year"] > 0:
            width = max(width, 1.0)  # a tiny but real rate still shows
        out.append(
            f'<div class="gt-row"><div class="gt-line"><strong>{html.escape(r["label"])}</strong>'
            f'<span>{html.escape(r["words"])}</span></div>'
            f'<div class="gt-bar" aria-hidden="true" style="width:{width:.1f}%;background:{colour}"></div></div>'
        )
    out.append("</div>")
    return "".join(out)


def then_and_now(result):
    cards = message.then_and_now(result)
    if not cards:  # e.g. a Typical day where every check happens 5 or more times a year
        return
    st.subheader("Then and now")
    st.markdown(message.THEN_AND_NOW_CAPTION)
    style = ["<style>.gt-rows{margin:0.2rem 0 0.4rem 0}.gt-row{margin-bottom:0.55rem}"
             ".gt-line{display:flex;justify-content:space-between;gap:0.8rem;font-size:0.9rem;margin-bottom:0.2rem}"
             ".gt-bar{height:6px;border-radius:3px}"
             ".gt-chip{font-size:0.75rem;font-weight:700;border-radius:1rem;padding:0.1rem 0.55rem;"
             "margin-left:0.4rem;vertical-align:middle}"
             ".gt-value{font-size:1.9rem;font-weight:700;line-height:1.2}.gt-note{font-size:0.85rem;opacity:0.8}"]
    for i, card in enumerate(cards):
        style.append(f".st-key-gt-card-{i}{{background:{CARD_TINT[card['check']['level']]}}}")
    st.markdown("".join(style) + "</style>", unsafe_allow_html=True)
    for i, card in enumerate(cards):
        level = card["check"]["level"]
        accent, ink = LEVEL_STYLE[level]
        with st.container(border=True, key=f"gt-card-{i}"):
            chip = (f' <span class="gt-chip" style="background:{accent};color:{ink}">{html.escape(card["chip"])}'
                    '</span>') if card["chip"] else ""
            st.markdown(f"{message.ICONS[card['key']]} **{card['title']}**{chip}", unsafe_allow_html=True)
            st.markdown(f'<span class="gt-value">{html.escape(card["value"])}</span> '
                        f'<span class="gt-note">{html.escape(card["value_note"])}</span>', unsafe_allow_html=True)
            if card["rows"]:
                st.markdown(card_rows(card["rows"], accent), unsafe_allow_html=True)
            for line in (card["never"], card["rarer_now"]):
                if line:
                    st.markdown(f"**{line}**")


def normal_section(result):
    lines = message.normal_lines(result)
    with st.expander(f"Normal for here ({len(lines)})"):  # written by code, never by Claude
        quiet = [f"{message.ICONS[key]}&nbsp; {label} &nbsp;·&nbsp; {value}" for key, label, value in lines]
        extra = message.not_enough_lines(result) + message.data_notes(result)
        if quiet or extra:
            st.markdown("  \n".join(quiet + extra))
        st.caption(message.NORMAL_SMALL_PRINT)


def how_sure_section():
    with st.expander("How sure are we"):
        st.markdown("\n".join(f"- {line}" for line in message.HOW_SURE_LINES))


def about_section(result):
    with st.expander("About this tool"):
        st.markdown(f"**How the level is set:** {message.HOW_LEVEL_SET}")
        st.markdown("**What the levels mean:**\n" + "\n".join(f"- {line}" for line in message.LEVELS_MEAN))
        st.markdown("\n".join(f"- {line}" for line in ABOUT_LINES))
        fc, hist = result.get("forecast_grid_point"), result.get("history_grid_point")
        if fc and hist:  # the sources
            st.caption(
                f"Forecast: {result['forecast_source']} (grid point {fc['latitude']:.2f}, {fc['longitude']:.2f}). "
                f"History: {result['history_source']} (grid point {hist['latitude']:.2f}, "
                f"{hist['longitude']:.2f}). Compared with {result['baseline_label']}; the level uses "
                f"{result['recent_label']} ({result['recent_phrase']})."
            )


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
    hero = None
    if result["level"] in risk.LEVELS[1:]:  # raised days only
        try:
            hero = message.hero_line(result, cached_history(lat, lon, result["date"], replay_name is not None))
        except Exception:  # no hero line rather than an error
            hero = None
    level_box(result, place, hero)
    special = replays.SPECIAL_NOTES.get(replay_name)
    title = message.headline(result)  # raised days only; written by code
    if title:
        st.markdown(f"### {title}")
    for line in message.summary_lines(result, special):
        if line == message.ICE_SMS:
            st.warning(line, icon="🧊")
        elif line == message.not_checked(result, special):
            st.warning(line, icon=":material/thunderstorm:")  # the page's visible pointer to official warnings
        else:
            st.markdown(line)  # the action line

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

    normal_section(result)
    how_sure_section()
    about_section(result)


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
