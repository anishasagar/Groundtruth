"""Checks on the page itself, every replay rendered with Streamlit's test runner (no Open-Meteo, no Claude).

Every word on the page is written by code: app.py never uses Claude (groundtruth/claude_text.py, kept for Phase 2).

Run from the project folder:  python tests/test_page.py
"""

import datetime as dt
import html
import re
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import geocode, message, replays, risk, weather  # noqa: E402

FOLDED = ["Normal for here ({n})", "How sure are we", "About this tool"]
NO_REPLAY = "— none, use the search above —"


def texts(elements):
    return [str(e.value) for e in elements]


def visible_text(at):
    """Everything on the page outside the collapsed sections."""
    out = []

    def walk(node):
        if getattr(node, "type", None) == "expander":
            return
        value = getattr(node, "value", None)
        if isinstance(value, str):
            out.append(value)
        for child in getattr(node, "children", {}).values():
            walk(child)
    walk(at.main)
    return "\n".join(out)


def all_text(at):
    """Everything on the page, the collapsed sections included."""
    out = []

    def walk(node):
        value = getattr(node, "value", None)
        if isinstance(value, str) and not value.lstrip().startswith(("<div", "<style")):
            out.append(value)
        for child in getattr(node, "children", {}).values():
            walk(child)
    walk(at.main)
    return out


def sentences(texts):
    """Every sentence on the page, markdown and list marks removed."""
    found = []
    for text in texts:
        text = re.sub(r"[*_#>]|^\s*-\s", " ", text, flags=re.M)
        found += [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n", text) if len(x.strip()) > 3]
    return found


def render(name):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    box = next(s for s in at.selectbox if s.label == "Or replay a past event")
    box.set_value(name).run()
    assert not at.exception, f"{name}: {at.exception}"
    return at


def no_claude_in_app():
    """app.py doesn't import or call Claude (CLAUDE.md rule 9: any Claude text must be marked; there is none)."""
    source = (ROOT / "app.py").read_text()
    code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
    assert "claude_text" not in code and "anthropic" not in code, "app.py uses Claude"
    print("ok: app.py doesn't use Claude")


def main():
    no_claude_in_app()
    for case in replays.load_replays():
        name = case["name"]
        at = render(name)
        warnings = texts(at.warning)
        used = []
        with weather.offline():
            result = risk.assess(float(case["latitude"]), float(case["longitude"]), dt.date.fromisoformat(case["date"]))
        # Yellow boxes: the ice box (on ice days) and the "Not checked" box on every result.
        special = replays.SPECIAL_NOTES.get(name)
        ice = [message.ICE_SMS] if message.ice_note(result) else []
        assert warnings == ice + [message.not_checked(result, special)], f"{name}: yellow boxes: {warnings}"
        assert [w.icon for w in at.warning] == ["🧊"] * len(ice) + [":material/thunderstorm:"], name
        # The level box: place · date, the level word, the hero line (raised days only), the value line.
        history = weather.get_history(float(case["latitude"]), float(case["longitude"]),
                                      *message.hero_history_range(result["date"]))["data"]
        hero = message.hero_line(result, history)
        box = next(m.value for m in at.markdown if 'role="status"' in m.value)
        assert hero is None or result["level"] in risk.LEVELS[1:], f"{name}: a hero line on a Typical day"
        if hero:
            shown_hero = html.escape(hero)
            assert f"font-weight:700;line-height:1.3;margin:0.15rem 0 0.2rem 0\">{shown_hero}</div>" in box, name
            assert box.index(result["level"]) < box.index(shown_hero) < box.index(message.level_line(result)), name
        else:
            assert "line-height:1.3" not in box, f"{name}: a hero line where there should be none"
        # The headline is written by code: "<Level> risk of <hazard>." on raised days, none on Typical days.
        title = message.headline(result)
        assert [h.value for h in at.markdown if h.value.startswith("### ")] == ([f"### {title}"] if title else []), name
        shown = visible_text(at)
        # The yellow line is the one visible pointer to official warnings.
        assert message.OFFICIAL_LINE not in shown and "Check your official weather warnings" not in shown, name
        assert "Text message" not in shown and "We check rain, heat" not in shown, f"{name}: removed sections"
        n = len(message.normal_lines(result))
        assert [e.label for e in at.expander] == [FOLDED[0].format(n=n), *FOLDED[1:]], \
            f"{name}: {[e.label for e in at.expander]}"
        assert not any(e.proto.expanded for e in at.expander), f"{name}: sections must start collapsed"
        everything = "\n".join(all_text(at))
        assert message.OFFICIAL_LINE in everything, f"{name}: official warnings missing from How sure are we"
        how_sure = next(e for e in at.expander if e.label == "How sure are we")
        assert [m.value for m in how_sure.markdown] == ["\n".join(f"- {x}" for x in message.HOW_SURE_LINES)], name
        assert "Written by Claude" not in everything and "The detailed numbers" not in everything, name
        assert "Template mode" not in everything and "how often days" not in everything.replace(
            message.THEN_AND_NOW_CAPTION, ""), f"{name}: template notes and per-block captions are gone"
        assert "are ignored" not in everything, f"{name}: the old replay note"
        said = sentences(all_text(at))
        twice = sorted({x for x in said if said.count(x) > 1})
        assert not twice, f"{name}: said twice on the page: {twice}"
        # The replay fills the place and date fields.
        assert at.text_input(key="query").value == replays.place_of(case), name
        assert at.date_input(key="date").value == dt.date.fromisoformat(case["date"]), name
        cards = message.then_and_now(result)
        assert ("Then and now" in texts(at.subheader)) == bool(cards), f"{name}: then and now"
        assert (message.THEN_AND_NOW_CAPTION in texts(at.markdown)) == bool(cards), name
        # One card per check, each with its icon, title and (raised checks only) its level chip.
        headers = [m.value for m in at.markdown if m.value.startswith(":material/") and "**" in m.value]
        assert len(headers) == len(cards), f"{name}: {len(headers)} card headers for {len(cards)} cards"
        for header, card in zip(headers, cards):
            assert header.startswith(f"{message.ICONS[card['key']]} **{card['title']}**"), header
            assert (f">{card['chip']}</span>" in header) == bool(card["chip"]), header
            for line in (card["never"], card["rarer_now"]):
                if line:
                    assert f"**{line}**" in texts(at.markdown), f"{name}: {line}"
            if card["rows"]:  # the bars: label, words, width on the shared scale
                bars = next(m.value for m in at.markdown if m.value.startswith('<div class="gt-rows">')
                            and card["rows"][0]["label"] in m.value and m.value not in used)
                used.append(bars)
            assert not card["rows"] or "gt-bar" in bars, name
        about = next(e for e in at.expander if e.label == "About this tool")
        about_text = [m.value for m in about.markdown]
        assert about_text[0] == f"**How the level is set:** {message.HOW_LEVEL_SET}", about_text[0]
        assert about_text[1] == "**What the levels mean:**\n" + "\n".join(f"- {x}" for x in message.LEVELS_MEAN)
        assert "fixed wording written by code" in about_text[2], name
        assert any(c.value.startswith("Forecast: ") for c in about.caption), f"{name}: sources in About this tool"
        normal = next(e for e in at.expander if e.label.startswith("Normal for here"))
        assert not any(c.value.startswith("Forecast: ") for c in normal.caption), f"{name}: sources moved"
        assert [c.value for c in normal.caption] == [message.NORMAL_SMALL_PRINT], name
        for key, label, value in message.normal_lines(result):
            assert f"{message.ICONS[key]}&nbsp; {label} &nbsp;·&nbsp; {value}" in normal.markdown[0].value, label
        assert "Next 48 hours" not in shown, f"{name}: no hourly strip on a replay"
        geological = special == "geological"
        assert (message.NOT_CHECKED_GEOLOGICAL_END in shown) == geological, f"{name}: geological authorities"
        assert message.GEOLOGICAL_NOTE not in shown, f"{name}: the separate geological note is gone"
        assert shown.count("Phase 2") == 2, f"{name}: the two Phase 2 cards"
        print(f"ok: {name}")

    # Changing the date switches the replay off; picking "none" clears the place. (No live search here.)
    search = geocode.search_places
    geocode.search_places = lambda query, count=10: []
    try:
        switch_off_cases()
    finally:
        geocode.search_places = search
    print("All page checks passed.")


def switch_off_cases():
    at = render("Paris snow and cold")
    at.date_input(key="date").set_value(dt.date(2026, 1, 8)).run()
    assert at.selectbox(key="replay").value == NO_REPLAY and at.text_input(key="query").value == "Paris, France"
    assert "No place found" in " ".join(e.value for e in at.info), "once off, the place is searched live"
    at = render("Paris snow and cold")
    at.text_input(key="query").set_value("Lyon").run()
    assert at.selectbox(key="replay").value == NO_REPLAY, "typing a place switches the replay off"
    at = render("Paris snow and cold")
    at.selectbox(key="replay").set_value(NO_REPLAY).run()
    assert at.text_input(key="query").value == "", "picking none clears the place"
    print("ok: changing the place or date switches the replay off")


if __name__ == "__main__":
    main()
