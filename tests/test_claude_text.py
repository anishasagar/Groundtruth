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

from groundtruth import claude_text, replays, risk, weather  # noqa: E402
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
NOT_COVERED = ("Our checks don't cover thunderstorms, freezing rain or ice on roads, or landslides and glacier "
               "collapse.")

GOOD_KOLKATA = {
    "headline": "High risk from heat in Kolkata, India on 31 May 2022.",
    "why": ["Feels-like heat reached 41 °C, above the 40 °C danger line, and that set the level.",
            "Heat like this happens about 48 times a year here now, 1.4 times more common here than in 1951–1980."],
    "what_it_means": "Avoid heavy exertion outdoors, drink water, and check on older or vulnerable people. "
                     "Check your official weather warnings.",
    "sms": "Kolkata 31 May 2022: High risk from heat, feels like 41 C. Drink water. Check official warnings.",
    "confidence_note": "The history is a grid of about 25 km and misses very local storms.",
}
GOOD_VALENCIA = {
    "headline": "Extreme risk of heavy rain in Paiporta, Valencia, Spain on 29 Oct 2024.",
    "why": ["Rain of 202 mm in 24 h, above the 150 mm danger line, set the level.",
            "Rain like this was not seen in 1951–1980 or in the 30 years before this date.",
            "Normal wind for here (gusts up to 61 km/h)."],
    "what_it_means": "Avoid underpasses, low roads and riverbanks. Check your official weather warnings.",
    "sms": "Extreme risk of heavy rain in Paiporta on 29 Oct 2024: 202 mm in 24 h. Check official warnings.",
    "confidence_note": "Thunderstorms are not checked, and the history misses very local storms.",
}


GOOD_PARIS = {
    "headline": "Typical rain, temperature, snow and wind for Paris, France on 7 Jan 2026.",
    "why": ["Snowfall set the level: normal snowfall for here (3.0 cm).",
            "Normal wind for here (gusts up to 36 km/h)."],
    "what_it_means": f"{NOT_COVERED} Check your official weather warnings.",
    "sms": "Groundtruth Paris 7 Jan 2026: Typical rain, temperature, snow and wind. Check official warnings.",
    "confidence_note": "Freezing rain and ice are not checked, and the history misses very local storms.",
}


def typical_reply(facts, short_place, what_it_means):
    """A good Typical reply for these facts: its why bullets copy the engine's own wording."""
    return {
        "headline": f"Typical rain, temperature, snow and wind for {facts['place']} on {facts['day']}.",
        "why": [c["wording"] for c in facts["checks"][:2]],
        "what_it_means": what_it_means,
        "sms": f"Groundtruth {short_place} {facts['day']}: Typical rain, temperature, snow and wind. "
               "Check official warnings.",
        "confidence_note": "The history misses very local storms.",
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
    expect_pass("good Kolkata reply", GOOD_KOLKATA, KOLKATA)
    expect_pass("good Valencia reply", GOOD_VALENCIA, VALENCIA)

    # Lowercase level words are ordinary words, not level labels.
    expect_pass('"daily high" on an Extreme day',
                changed(GOOD_VALENCIA, why=[*GOOD_VALENCIA["why"][:2], "The daily high felt like up to 20 °C."]),
                VALENCIA)
    expect_pass('"extreme heat" on a High day',
                changed(GOOD_KOLKATA, what_it_means="In extreme heat, avoid heavy exertion outdoors and drink water. "
                                                    "Check your official weather warnings."), KOLKATA)
    expect_pass('"typical for October" on an Extreme day',
                changed(GOOD_VALENCIA, confidence_note="Rain like this is not typical for October here, and the "
                                                       "history misses very local storms."), VALENCIA)
    expect_fail("a capitalised other level label",
                why_with(GOOD_KOLKATA, "Rain was Typical."), KOLKATA, "names another level (Typical)")

    # Typical days: the headline says what is typical; no broad "typical weather" without that scope.
    expect_pass("good Paris (Typical) reply", GOOD_PARIS, PARIS)
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
    expect_fail('"Typical weather" in the SMS',
                changed(GOOD_PARIS, sms="Groundtruth Paris 7 Jan 2026: Typical weather. Check official warnings."),
                PARIS, '"Typical weather" without saying what it covers')
    expect_pass('"normal conditions" followed by its scope',
                why_with(GOOD_PARIS, "These are normal conditions for the rain, temperature, snow and wind we check."),
                PARIS)
    expect_pass('"typical weather" on a High day is checked too, and passes with its scope',
                why_with(GOOD_KOLKATA, "Apart from heat, this was typical weather for the rain, snow and wind we "
                                       "check, and for the cold."), KOLKATA)
    expect_fail('"typical weather" on a High day without its scope',
                why_with(GOOD_KOLKATA, "Apart from the heat it was typical weather."), KOLKATA, "without saying")

    # A Typical day must not sound like an all-clear.
    for words, label in [("Nothing stands out for this place on this day.", "nothing stands out"),
                         ("Nothing in the checks stood out.", "nothing stands out"),
                         ("This day does not stand out.", "nothing stands out"),
                         ("Nothing unusual is forecast.", "nothing unusual"),
                         ("Nothing in the checks points to unusual weather.", "nothing unusual"),
                         ("The checks do not show an unusual day for this place.", "nothing unusual"),
                         ("The checks don't find anything unusual.", "nothing unusual"),
                         ("There is nothing to worry about.", "nothing to worry about"),
                         ("There is no cause for concern.", "no concern"),
                         ("Everything looks fine.", "everything is fine"),
                         ("It is a quiet day.", "a quiet day")]:
        expect_fail(f'all-clear: "{words}"',
                    changed(GOOD_PARIS, what_it_means=f"{words} {GOOD_PARIS['what_it_means']}"),
                    PARIS, f'("{label}")')
    for left_out, text in [("thunderstorms", "Our checks don't cover freezing rain or ice on roads, or landslides."),
                           ("ice", "Our checks don't cover thunderstorms or landslides."),
                           ("landslides or glacier collapse", "Our checks don't cover thunderstorms or ice.")]:
        expect_fail(f"Typical day: what it means leaves out {left_out}",
                    changed(GOOD_PARIS, what_it_means=f"{text} Check your official weather warnings."),
                    PARIS, f"(missing: {left_out})")
    expect_pass("a High day doesn't need the not-covered list", GOOD_KOLKATA, KOLKATA)
    expect_fail("what it means doesn't end with official warnings",
                changed(GOOD_PARIS, what_it_means=f"Check your official weather warnings. {NOT_COVERED}"),
                PARIS, "doesn't end by pointing to official warnings")
    expect_fail("High day: official warnings not last",
                changed(GOOD_KOLKATA, what_it_means="Check your official weather warnings. Drink water."),
                KOLKATA, "doesn't end by pointing to official warnings")

    # Where a special note applies, what it means must mention it.
    assert BAYESIAN["special_note_kind"] == "storm" and NEPAL["special_note_kind"] == "geological"
    assert PARIS["special_note_kind"] is None and PARIS["special_note"] is None
    expect_fail("Bayesian without the storm note", typical_reply(BAYESIAN, "Porticello", f"{NOT_COVERED} Check "
                                                                 "your official weather warnings."),
                BAYESIAN, "storm note")
    expect_pass("Bayesian with the storm note",
                typical_reply(BAYESIAN, "Porticello", f"{NOT_COVERED} Storms are a major cause of weather deaths, "
                                                      "so follow official storm warnings."), BAYESIAN)
    expect_fail("Nepal-Tibet without the geological note", typical_reply(NEPAL, "Nepal-Tibet", f"{NOT_COVERED} "
                                                                        "Check your official weather warnings."),
                NEPAL, "geological note")
    expect_pass("Nepal-Tibet with the geological note",
                typical_reply(NEPAL, "Nepal-Tibet", f"{NOT_COVERED} For glacier collapse and landslides, check local "
                                                    "civil protection and geological authorities. Check your "
                                                    "official weather warnings."), NEPAL)

    # "Deciding check" stays out of the headline, and plain words are used instead of the term.
    expect_fail('"deciding check" in the headline',
                changed(GOOD_PARIS, headline="Typical rain, temperature, snow and wind for Paris, France on "
                                             "7 Jan 2026, with snowfall the deciding check."),
                PARIS, 'headline mentions the "deciding check"')
    expect_fail('"deciding check" in a bullet', why_with(GOOD_PARIS, "Snowfall was the deciding check."),
                PARIS, 'term "deciding check"')

    # Wrong level.
    expect_fail("wrong level", changed(GOOD_KOLKATA, headline="Extreme risk from heat in Kolkata on 31 May 2022.",
                                       sms=GOOD_KOLKATA["sms"].replace("High", "Extreme")),
                KOLKATA, 'doesn\'t say the level "High"')
    expect_fail("level missing from the SMS", changed(GOOD_KOLKATA, sms="Kolkata 31 May 2022: hot. Check official "
                                                                         "warnings."), KOLKATA, "text message")

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

    # Text message, bullets, official warnings.
    expect_fail("SMS too long", changed(GOOD_KOLKATA, sms=GOOD_KOLKATA["sms"] + " " + "x" * 100), KOLKATA,
                "characters (at most 160)")
    expect_fail("SMS not plain ASCII", changed(GOOD_KOLKATA, sms=GOOD_KOLKATA["sms"].replace("41 C", "41 °C")),
                KOLKATA, "plain ASCII")
    expect_fail("1 why bullet", changed(GOOD_KOLKATA, why=GOOD_KOLKATA["why"][:1]), KOLKATA, "1 why bullets")
    expect_fail("5 why bullets", changed(GOOD_KOLKATA, why=GOOD_KOLKATA["why"] * 2 + GOOD_KOLKATA["why"][:1]),
                KOLKATA, "5 why bullets")
    expect_fail("no official warnings", changed(GOOD_KOLKATA, what_it_means="Drink water."), KOLKATA,
                "official warnings")
    expect_fail("missing part", {k: v for k, v in GOOD_KOLKATA.items() if k != "sms"}, KOLKATA, "expected parts")


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
    client_cases()
    not_enough_cases()
    facts_cases()
    saved_reply_cases()
    print("All Claude text checks passed.")


if __name__ == "__main__":
    main()
