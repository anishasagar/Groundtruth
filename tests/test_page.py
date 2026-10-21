"""Checks on the page itself, every replay rendered with Streamlit's test runner (no Open-Meteo, no Claude).

Run from the project folder:  python tests/test_page.py
"""

import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import message, replays  # noqa: E402

FOLDED = ["The numbers", "How sure are we", "About this tool"]


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


def render(name):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60)
    at.run()
    box = next(s for s in at.selectbox if s.label == "Or replay a past event")
    box.set_value(name).run()
    assert not at.exception, f"{name}: {at.exception}"
    return at


def main():
    for case in replays.load_replays():
        name = case["name"]
        at = render(name)
        warnings = texts(at.warning)
        assert warnings.count(message.STORM_LINE) == 1, f"{name}: the yellow storm line: {warnings}"
        assert len(warnings) == 1, f"{name}: one yellow line only: {warnings}"
        shown = visible_text(at)
        # The yellow line is the one visible pointer to official warnings.
        assert message.OFFICIAL_LINE not in shown and "Check your official weather warnings" not in shown, name
        assert "Text message" not in shown and "We check rain, heat" not in shown, f"{name}: removed sections"
        assert [e.label for e in at.expander] == FOLDED, f"{name}: {[e.label for e in at.expander]}"
        assert not any(e.proto.expanded for e in at.expander), f"{name}: sections must start collapsed"
        all_text = "\n".join(str(getattr(e, "value", "")) for e in at.markdown)
        assert message.OFFICIAL_LINE in all_text, f"{name}: official warnings missing from How sure are we"
        assert "Then and now" in texts(at.subheader), f"{name}: then and now"
        assert "Next 48 hours" not in shown, f"{name}: no hourly strip on a replay"
        geological = replays.SPECIAL_NOTES.get(name) == "geological"
        assert (message.GEOLOGICAL_NOTE in shown) == geological, f"{name}: geological note"
        assert shown.count("Phase 2") == 2, f"{name}: the two Phase 2 cards"
        print(f"ok: {name}")
    print("All page checks passed.")


if __name__ == "__main__":
    main()
