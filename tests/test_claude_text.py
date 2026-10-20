"""Checks on the Claude-written text. Run from the project folder:  python tests/test_claude_text.py

Never calls Claude or Open-Meteo:
1. The guardrail: good replies pass; replies that break a rule fail with a reason.
2. Fake Claude clients that time out, fail or answer badly lead to template mode.
3. "Not enough data" never goes to Claude.
4. The facts never include coordinates, grid points or source names.
5. Every saved replay reply is up to date and passes the guardrail.
"""

import copy
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import anthropic
import httpx2

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from groundtruth import claude_text, message, replays, risk, weather  # noqa: E402
from test_message import fake_assess  # noqa: E402

TODAY = dt.date(2026, 10, 19)


def replay_facts(name):
    case = {c["name"]: c for c in replays.load_replays()}[name]
    with weather.offline():
        result = risk.assess(float(case["latitude"]), float(case["longitude"]), dt.date.fromisoformat(case["date"]))
    return claude_text.facts(result, replays.place_of(case), TODAY, replays.SPECIAL_NOTES.get(name)), case


KOLKATA, _ = replay_facts("Kolkata heat (KK concert)")
VALENCIA, _ = replay_facts("Valencia flash flood")
PARIS, _ = replay_facts("Paris snow and cold")
BAYESIAN, _ = replay_facts("Bayesian sinking")
NEPAL, _ = replay_facts("Nepal-Tibet glacier-collapse flood")
TEXAS, _ = replay_facts("Texas Hill Country flood")
CONFIDENCE = ("The history is a grid of about 25 km and misses very local storms, and the day's figures are a "
              "forecast and can be too low.")

GOOD_KOLKATA = {
    "headline": "High risk from heat in Kolkata, India on 31 May 2022.",
    "why": ["Feels-like heat is forecast at 41 °C, above the 40 °C danger line, and that set the level.",
            "Heat like this happens about 48 times a year here now, 1.4 times more common here than in 1951–1980."],
    "confidence_note": CONFIDENCE,
}
GOOD_VALENCIA = {
    "headline": "Extreme risk of heavy rain in Paiporta, Valencia, Spain on 29 Oct 2024.",
    "why": ["Rain of 202 mm in 24 h is forecast, above the 150 mm danger line, and set the level.",
            "Rain like this was not seen in 1951–1980 or in the 30 years before this date.",
            "Normal wind for here (gusts up to 61 km/h; the data misses sudden local storm gusts)."],
    "confidence_note": "Thunderstorms are not checked, the history is a grid of about 25 km that misses very local "
                       "storms, and the day's figures are a forecast.",
}
GOOD_PARIS = {
    "headline": "Typical rain, temperature, snow and wind for Paris, France on 7 Jan 2026.",
    "why": ["Snowfall set the level: normal snowfall for here (3.0 cm).",
            "Normal wind for here (gusts up to 36 km/h; the data misses sudden local storm gusts)."],
    "confidence_note": "Freezing rain and ice are not checked, the history is a grid of about 25 km that misses very "
                       "local storms, and the day's figures are a forecast.",
}
GOOD_TEXAS = {
    "headline": "High risk of heavy rain in Texas Hill Country, USA on 4 Jul 2025.",
    "why": ["Rain over 24 h set the level, with 107 mm forecast.",
            "Rain like this happens about once every 15 years here now."],
    "confidence_note": CONFIDENCE,
}


def typical_reply(facts):
    """A good Typical reply for these facts: its why bullets copy the engine's own wording."""
    return {
        "headline": f"Typical rain, temperature, snow and wind for {facts['place']} on {facts['day']}.",
        "why": [c["wording"] for c in facts["checks"][:2]],
        "confidence_note": CONFIDENCE,
    }


def changed(reply, **parts):
    out = copy.deepcopy(reply)
    out.update(parts)
    return out


def why_with(reply, bullet):
    return changed(reply, why=[*reply["why"], bullet])


def expect_pass(label, reply, facts):
    problems = claude_text.check_reply(reply, facts)
    assert not problems, f"{label}: should pass, but: {problems}"
    print(f"ok: passes: {label}")


def expect_fail(label, reply, facts, reason):
    problems = claude_text.check_reply(reply, facts)
    assert any(reason in p for p in problems), f"{label}: expected a reason containing {reason!r}, got {problems}"
    print(f"ok: fails: {label} -> {'; '.join(problems)}")


def guardrail_cases():
    for label, reply, facts in [("Kolkata", GOOD_KOLKATA, KOLKATA), ("Valencia", GOOD_VALENCIA, VALENCIA),
                                ("Paris (Typical)", GOOD_PARIS, PARIS), ("Texas", GOOD_TEXAS, TEXAS),
                                ("Bayesian (Typical)", typical_reply(BAYESIAN), BAYESIAN),
                                ("Nepal-Tibet (Typical)", typical_reply(NEPAL), NEPAL)]:
        expect_pass(f"good {label} reply", reply, facts)

    # Claude writes only the headline, the why bullets and the confidence note.
    for extra in ("what_it_means", "sms"):
        expect_fail(f"a reply that still writes {extra}", changed(GOOD_KOLKATA, **{extra: "Check official warnings."}),
                    KOLKATA, "expected parts")
    expect_fail("missing part", {k: v for k, v in GOOD_KOLKATA.items() if k != "confidence_note"}, KOLKATA,
                "expected parts")
    for name in ("action_line", "sms_action", "official_warnings", "ice_note"):
        assert name not in PARIS, f"{name} is written by code now, so Claude doesn't get it"

    # Lowercase higher level words are ordinary words; a capitalised other level label is not.
    expect_pass('"daily high" on an Extreme day',
                changed(GOOD_VALENCIA, why=[*GOOD_VALENCIA["why"][:2], "The daily high is forecast to feel like up "
                                                                       "to 20 °C."]), VALENCIA)
    expect_pass('"extreme heat" on a High day', why_with(GOOD_KOLKATA, "This matters most in extreme heat."), KOLKATA)
    expect_fail("a capitalised other level label", why_with(GOOD_KOLKATA, "Rain was Typical."), KOLKATA,
                "names another level (Typical)")
    expect_fail('"typical for October" on an Extreme day',
                why_with(GOOD_VALENCIA, "Rain like this is not typical for October here."), VALENCIA,
                "lower level word (Typical)")
    expect_fail('"typical weather" on a High day, even with its scope, uses a lower level word',
                why_with(GOOD_KOLKATA, "Apart from heat, this was typical weather for the rain, snow and wind we "
                                       "check, and for the cold."), KOLKATA, "lower level word (Typical)")
    expect_fail("wrong level", changed(GOOD_KOLKATA, headline="Extreme risk from heat in Kolkata on 31 May 2022."),
                KOLKATA, 'doesn\'t say the level "High"')

    # Typical days: the headline says what is typical; no broad "typical weather" without that scope.
    expect_pass("Typical headline with heat and cold for temperature",
                changed(GOOD_PARIS, headline="Typical rain, heat, cold, snow and wind for Paris, France on "
                                             "7 Jan 2026."), PARIS)
    expect_fail('"Typical weather" headline', changed(GOOD_PARIS, headline="Typical weather in Paris, France on "
                                                                          "7 Jan 2026."),
                PARIS, "doesn't say what is typical (missing: rain, temperature, snow, wind)")
    expect_fail("Typical headline missing wind", changed(GOOD_PARIS, headline="Typical rain, temperature and snow "
                                                                             "for Paris, France on 7 Jan 2026."),
                PARIS, "(missing: wind)")
    for phrase in ("typical weather", "typical conditions", "typical day", "normal weather", "normal conditions"):
        expect_fail(f'"{phrase}" in a bullet', why_with(GOOD_PARIS, f"It was a {phrase} for Paris."),
                    PARIS, f'"{phrase}" without saying what it covers')
    expect_pass('"normal conditions" followed by its scope',
                why_with(GOOD_PARIS, "These are normal conditions for the rain, temperature, snow and wind we check."),
                PARIS)
    for words in ("This matches the wording.", "These were in the facts for the day."):
        expect_fail(f'talks about the prompt: "{words}"', why_with(GOOD_PARIS, words), PARIS, "talks about the facts")

    # Nothing may sound like an all-clear, on any day.
    for words, label in [("Nothing stands out for this place on this day.", "nothing stands out"),
                         ("Nothing in the checks stood out.", "nothing stands out"),
                         ("This day does not stand out.", "nothing stands out"),
                         ("Nothing unusual is forecast.", "nothing unusual"),
                         ("The checks don't find anything unusual.", "nothing unusual"),
                         ("There is nothing to worry about.", "nothing to worry about"),
                         ("There is no cause for concern.", "no concern"),
                         ("Everything looks fine.", "everything is fine"),
                         ("It is a quiet day.", "a quiet day")]:
        expect_fail(f'all-clear: "{words}"', why_with(GOOD_PARIS, words), PARIS, f'("{label}")')

    # "Deciding check" stays out, plain words instead.
    expect_fail('"deciding check" in the headline',
                changed(GOOD_PARIS, headline="Typical rain, temperature, snow and wind for Paris, France on "
                                             "7 Jan 2026, with snowfall the deciding check."),
                PARIS, 'headline mentions the "deciding check"')
    expect_fail('"deciding check" in a bullet', why_with(GOOD_PARIS, "Snowfall was the deciding check."),
                PARIS, 'term "deciding check"')

    # Numbers: extra, rounded, more precise, written as words.
    expect_fail("extra number", why_with(GOOD_KOLKATA, "It was the hottest day in 12 years."), KOLKATA, "(12)")
    expect_fail("rounded number", changed(GOOD_VALENCIA, headline="Extreme risk of heavy rain in Paiporta on "
                                                                 "29 Oct 2024: about 200 mm."), VALENCIA, "(200)")
    expect_fail("number with a decimal added", changed(GOOD_KOLKATA, why=["Feels like 41.3 °C, above the 40 °C "
                                                                          "danger line.", GOOD_KOLKATA["why"][1]]),
                KOLKATA, "(41.3)")
    expect_fail("number written as a word", why_with(GOOD_KOLKATA, "Days like this are now twice as frequent."),
                KOLKATA, "as words (twice)")
    expect_fail("minus sign added", why_with(GOOD_KOLKATA, "The low felt like -34 °C."), KOLKATA, "(-34)")

    # Banned words and claims.
    for words, label in [("You are safe outdoors.", "safe"), ("It's all clear after dark.", "all clear"),
                         ("There is no risk at night.", "no risk"), ("There is no hazard at night.", "no hazard"),
                         ("Climate change caused this heat.", "caused"),
                         ("Climate change is the cause of this heat.", "caused"),
                         ("Climate change made this 3 times more likely.", "more likely"),
                         ("This heat is due to climate change.", "blames climate change")]:
        expect_fail(f'banned: "{label}"', why_with(GOOD_KOLKATA, words), KOLKATA, f'("{label}")')
    expect_fail('"less common"', why_with(GOOD_VALENCIA, "Cold days like this are less common now."),
                VALENCIA, '("less common")')
    # A check that is less common now than in 1951–1980 needs the "not less serious" note right there.
    reassuring = "Days this cold happened about 246 times a year in 1951–1980."
    expect_fail("less common now, said reassuringly", why_with(GOOD_VALENCIA, reassuring), VALENCIA,
                "more frequent in 1951–1980")
    expect_pass("less common now, with the note",
                changed(GOOD_VALENCIA, why=[*GOOD_VALENCIA["why"][:2], reassuring,
                                            "That doesn't make today any less serious: the level is based on the "
                                            "recent 30 years."]), VALENCIA)

    # "Normal" only directly before what a check measures.
    expect_fail('misused "normal"', why_with(GOOD_KOLKATA, "Everything else was normal."), KOLKATA, '"normal"')
    expect_fail('"normal" after the thing', why_with(GOOD_KOLKATA, "Wind was normal for here."), KOLKATA, '"normal"')
    expect_fail('"normally"', why_with(GOOD_KOLKATA, "It is normally this hot."), KOLKATA, '"normal"')
    expect_pass('"normal" before a measured thing', why_with(GOOD_KOLKATA, "Normal rain for here (8.2 mm)."), KOLKATA)
    expect_fail('"normal wind" without the limit', why_with(GOOD_PARIS, "Normal wind for here (gusts up to 36 km/h)."),
                PARIS, "data misses sudden local storm gusts")

    # Bullets.
    expect_fail("1 why bullet", changed(GOOD_KOLKATA, why=GOOD_KOLKATA["why"][:1]), KOLKATA, "1 why bullets")
    expect_fail("5 why bullets", changed(GOOD_KOLKATA, why=GOOD_KOLKATA["why"] * 2 + GOOD_KOLKATA["why"][:1]),
                KOLKATA, "5 why bullets")


def review_rule_cases():
    """The rules added after the false-reassurance reviews."""
    # The confidence note says what the data can't see.
    for left_out, words in [("the 25 km grid", "The history misses very local storms; the day is a forecast."),
                            ("very local storms", "The history is a grid of about 25 km; the day is a forecast."),
                            ("that the day's figures are a forecast",
                             "The history is a grid of about 25 km and misses very local storms.")]:
        expect_fail(f"confidence note without {left_out}", changed(GOOD_KOLKATA, confidence_note=words), KOLKATA,
                    f"confidence note doesn't mention {left_out}")

    # Softening words and reassuring phrases: banned on every day.
    for words, label in [("Paris, France on 7 Jan 2026: a calm, low risk day.", "low risk"),
                         ("It is a calm day.", "calm"), ("The cold is mild.", "mild"),
                         ("It is a pleasant day.", "pleasant"), ("There are no warnings for Paris.", "no warnings"),
                         ("You can go ahead with your plans.", "go ahead"), ("This is a minimal risk.", "low risk"),
                         ("There is no need to change plans.", "no need"),
                         ("No special precautions are needed for rain, heat, cold, snow or wind.", "no precautions"),
                         ("No precautions are needed.", "no precautions"),
                         ("Outdoor plans can go on as planned.", "as planned"),
                         ("Outdoor plans can continue.", "can continue"), ("You can carry on as usual.", "carry on"),
                         ("It is fine to travel.", "fine to")]:
        expect_fail(f'reassuring on a Typical day: "{label}"', why_with(GOOD_PARIS, words), PARIS, f'("{label}")')
    expect_pass("a real warning with continue and precautions on an Extreme day",
                why_with(GOOD_VALENCIA, "Heavy rain will continue overnight; take precautions."), VALENCIA)

    # Elevated or higher: nothing softens the level.
    for words, label in [("The risk is slightly raised.", "slightly"), ("It is a bit hotter.", "a bit"),
                         ("Heat is a little above the line.", "a bit"), ("Expect minor discomfort.", "minor"),
                         ("It is only hot in the afternoon.", "only"), ("The heat is moderate at night.", "moderate"),
                         ("Winds stay light.", "light"), ("The heat is brief.", "brief"),
                         ("Hot spots are isolated.", "isolated"), ("It is somewhat hotter.", "somewhat"),
                         ("It is fairly hot.", "fairly"), ("It is relatively hot.", "relatively"),
                         ("It is just above the line.", "just"), ("The heat is manageable.", "manageable")]:
        expect_fail(f'softening on a High day: "{label}"', why_with(GOOD_KOLKATA, words), KOLKATA,
                    f'softens the level ("{label}")')
    expect_fail("the reviewer's example on an Extreme day", why_with(GOOD_VALENCIA, "The rain was brief and isolated."),
                VALENCIA, 'softens the level ("brief")')
    expect_pass('"moderate" on a Typical day is not checked as softening',
                why_with(GOOD_PARIS, "Gusts are moderate."), PARIS)
    expect_pass('"weather-driven hazards only" on a High day',
                changed(GOOD_KOLKATA, confidence_note=CONFIDENCE + " Groundtruth covers weather-driven hazards only."),
                KOLKATA)
    expect_fail('lowercase "elevated" on a High day', why_with(GOOD_KOLKATA, "The risk is elevated."), KOLKATA,
                "lower level word (Elevated)")
    expect_fail('"high risk" in lowercase on an Extreme day', why_with(GOOD_VALENCIA, "This is a high risk day."),
                VALENCIA, "lower level word (High)")

    # Climate change is never mentioned (the facts never mention it).
    for words in ("Climate change is making days like this 1.4 times more common here than in 1951–1980.",
                  "This is a sign of global warming.", "Warming has made heat like this more frequent."):
        expect_fail(f'climate: "{words[:40]}…"', why_with(GOOD_KOLKATA, words), KOLKATA, '("climate change")')

    # "Rarer" and "fewer" are banned like "less common".
    for words in ("Snow like this is 1.2 times rarer here than in 1951–1980.", "There are fewer days like this now.",
                  "Days like this happen less often now."):
        expect_fail(f'less common: "{words[:40]}…"', why_with(GOOD_PARIS, words), PARIS, '("less common")')

    # When a danger line set the level: say "danger line" in a bullet, and never call that check routine.
    heat = next(c for c in KOLKATA["checks"] if c["name"] == "Feels-like heat")
    assert heat["danger_line_note"] == message.DANGER_LINE_NOTE, heat
    assert not any(c.get("danger_line_note") for c in VALENCIA["checks"])  # rarity set Valencia's level too
    expect_fail("danger line set the level, but no bullet says so",
                changed(GOOD_KOLKATA, why=["Feels-like heat set the level, at 41 °C.",
                                           "Days like this happen about 48 times a year here now."]), KOLKATA,
                'no why bullet says "danger line"')
    expect_fail('"danger line" only in the confidence note',
                changed(GOOD_KOLKATA, why=["Feels-like heat set the level, at 41 °C.", GOOD_KOLKATA["why"][1]],
                        confidence_note=CONFIDENCE + " The danger line is 40 °C."), KOLKATA,
                'no why bullet says "danger line"')
    for words, found in [("Heat like this is common here.", "common"), ("Days like this are usual in May.", "usual"),
                         ("Heat like this is routine for Kolkata.", "routine")]:
        expect_fail(f'danger line set the level, but "{found}"', why_with(GOOD_KOLKATA, words), KOLKATA,
                    f'crossed its danger line routine ("{found}")')

    # A danger line is mentioned only when it was crossed.
    expect_fail("Texas: below the danger line",
                changed(GOOD_TEXAS, why=["Rain over 24 h set the level, with 107 mm forecast, which is below the "
                                         "danger line of 150 mm.", GOOD_TEXAS["why"][1]]), TEXAS,
                "danger line that wasn't crossed")
    expect_fail("Typical day: any danger line", why_with(GOOD_PARIS, "No danger line was crossed."), PARIS,
                "danger line that wasn't crossed")


# ---- fake Claude clients ----------------------------------------------------

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def answer(reply=None, text=None, stop_reason="end_turn"):
    text = json.dumps(reply) if text is None else text
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


class FakeClient:
    """Plays back a list of answers or errors, one per call."""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.messages = self

    def with_options(self, **_):
        return self

    def create(self, **request):
        assert request["model"] == claude_text.MODEL and "json_schema" in json.dumps(request["output_config"])
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class NeverCall(FakeClient):
    def create(self, **request):
        raise AssertionError("Claude must not be asked")


def expect_template(label, client, reason, calls):
    reply, problems = claude_text.write(KOLKATA, client)
    assert reply is None, f"{label}: should be template mode"
    assert any(reason in p for p in problems), f"{label}: {problems}"
    assert client is None or client.calls == calls, f"{label}: {client.calls} calls, expected {calls}"
    print(f"ok: template mode: {label} -> {claude_text.short_reason(problems)}")


def client_cases():
    timeout = anthropic.APITimeoutError(request=REQUEST)
    error = anthropic.InternalServerError("overloaded", response=httpx2.Response(500, request=REQUEST), body=None)
    offline = anthropic.APIConnectionError(request=REQUEST)

    expect_template("timeout twice (one retry)", FakeClient(timeout, timeout), "took too long", 2)
    expect_template("API error", FakeClient(error, error), "error (500)", 2)
    expect_template("connection error", FakeClient(offline, offline), "couldn't be reached", 2)
    expect_template("refusal", FakeClient(answer(GOOD_KOLKATA, stop_reason="refusal"), answer(text="")),
                    "declined", 2)
    expect_template("cut off", FakeClient(answer(text='{"headline": "Hi', stop_reason="max_tokens"),
                                          answer(text="{")), "cut off", 2)
    expect_template("broken JSON", FakeClient(answer(text="not json"), answer(text="[1, 2]")), "couldn't be read", 2)
    expect_template("unexpected error", FakeClient(RuntimeError("boom"), RuntimeError("boom")),
                    "something went wrong", 2)
    bad = changed(GOOD_KOLKATA, why=["Feels like 41.3 °C.", GOOD_KOLKATA["why"][1]])
    expect_template("bad reply twice", FakeClient(answer(bad), answer(bad)), "(41.3)", 2)
    expect_template("no key", None, "no Claude key", 0)

    reply, problems = claude_text.write(KOLKATA, FakeClient(timeout, answer(GOOD_KOLKATA)))
    assert reply == GOOD_KOLKATA and problems == ["Claude took too long to answer"], problems
    print("ok: a timeout, then a good reply on the retry -> Claude mode")
    client = FakeClient(answer(bad), answer(bad), answer(bad), answer(GOOD_KOLKATA))
    reply, problems = claude_text.write(KOLKATA, client, attempts=claude_text.CACHE_ATTEMPTS)
    assert reply == GOOD_KOLKATA and client.calls == 4 and len(problems) == 3, problems
    print("ok: filling the saved replies retries up to 3 times")


def not_enough_cases():
    result, _ = fake_assess(rain_mm=None)
    assert result["level"] == risk.NOT_ENOUGH, result["level"]
    facts = claude_text.facts(result, "Somewhere", TODAY)
    reply, problems = claude_text.write(facts, NeverCall())
    assert reply is None and "not enough data" in problems[0], problems
    reply, problems = claude_text.saved_reply(ROOT / "no-such-file.json", facts)
    assert reply is None and "not enough data" in problems[0], problems
    print("ok: Not enough data -> template mode, Claude never asked")


def facts_cases():
    for case in replays.load_replays():
        facts, _ = replay_facts(case["name"])
        text = claude_text.facts_json(facts)
        for word in ("latitude", "longitude", "grid point", "grid_point", "ERA5", "Open-Meteo", "Historical"):
            assert word not in text, f"{case['name']}: facts mention {word}"
        for coordinate in (case["latitude"], case["longitude"]):
            assert coordinate.lstrip("-") not in text, f"{case['name']}: facts contain {coordinate}"
        assert facts["level"] in risk.LEVELS and json.loads(text) == facts
    print("ok: facts have no coordinates, grid points or source names")


def saved_reply_cases():
    for case in replays.load_replays():
        facts, _ = replay_facts(case["name"])
        path = replays.claude_reply_file(case["name"])
        reply, problems = claude_text.saved_reply(path, facts)
        assert reply is not None, f"{case['name']}: saved reply not usable: {problems} " \
                                  "(run python scripts/save_claude_replies.py)"
        print(f"ok: saved reply up to date and passes: {case['name']}")

    # A saved reply with one number changed is rejected; so is one saved for different facts.
    source = replays.claude_reply_file("Kolkata heat (KK concert)")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / source.name
        shutil.copy(source, path)
        saved = json.loads(path.read_text())
        saved["reply"]["headline"] = saved["reply"]["headline"].rstrip(".") + ", feeling like 43 °C."
        path.write_text(json.dumps(saved))
        reply, problems = claude_text.saved_reply(path, KOLKATA)
        assert reply is None and "(43)" in problems[-1], problems
        reply, problems = claude_text.saved_reply(source, {**KOLKATA, "place": "Kolkata"})
        assert reply is None and "out of date" in problems[-1], problems
    print("ok: tampered or out-of-date saved replies -> template mode")


def main():
    guardrail_cases()
    review_rule_cases()
    client_cases()
    not_enough_cases()
    facts_cases()
    saved_reply_cases()
    print("All Claude text checks passed.")


if __name__ == "__main__":
    main()
