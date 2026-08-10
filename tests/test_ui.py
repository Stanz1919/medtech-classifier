"""Smoke tests for the Streamlit UI (ui/app.py), using Streamlit's own
streamlit.testing.v1.AppTest harness - it runs the real app script in a
simulated session and lets us assert on the resulting widget tree,
rather than needing a browser.

These are deliberately smoke-level, not a re-test of the extractor or
rules engine (those already have their own exhaustive suites) - the
point here is confirming the UI wiring itself doesn't crash and shows
the right headline result for a few known cases, in both input modes
and both the happy and error paths.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from ui.examples import JSON_EXAMPLES, TEXT_EXAMPLES

APP_PATH = str(Path(__file__).resolve().parent.parent / "ui" / "app.py")


def _fresh_app() -> AppTest:
    at = AppTest.from_file(APP_PATH)
    at.run()
    assert not at.exception, f"App raised on initial load: {at.exception}"
    return at


def _classify_via_text_example(at: AppTest, example_key: str) -> AppTest:
    at.sidebar.selectbox[0].select(example_key).run()
    at.sidebar.button[0].click().run()
    return at


def _classify_via_json_example(at: AppTest, example_key: str) -> AppTest:
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.selectbox[0].select(example_key).run()
    at.sidebar.button[0].click().run()
    return at


def test_initial_state_shows_prompt_and_no_result():
    at = _fresh_app()
    assert len(at.metric) == 0
    assert any("Classify" in i.value for i in at.info)


def test_all_text_examples_run_without_exception():
    """Every curated example must actually work - a broken demo example
    would be an embarrassing, avoidable bug in a portfolio piece."""
    for key in TEXT_EXAMPLES:
        at = _fresh_app()
        _classify_via_text_example(at, key)
        assert not at.exception, f"{key!r} raised: {at.exception}"
        assert len(at.metric) == 1, f"{key!r} did not produce a classification metric"


@pytest.mark.parametrize(
    "example_key,expected_class",
    [
        ("Hypodermic syringe (Class IIa)", "Class IIa"),
        ("Hip replacement implant (Class III)", "Class III"),
        ("Cardiac pacemaker (Class III)", "Class III"),
        ("Drug-eluting coronary stent (Class III)", "Class III"),
        ("Gauze wound dressing (Class I)", "Class I"),
        ("Reusable surgical scissors (Class I, via Rule 6)", "Class I"),
        ("Dental filling (Class IIa, via Rule 8)", "Class IIa"),
    ],
)
def test_text_example_reaches_expected_class(example_key, expected_class):
    at = _fresh_app()
    _classify_via_text_example(at, example_key)
    assert at.metric[0].value == expected_class


def test_heartbeat_app_example_surfaces_clarifying_questions_and_conservative_floor():
    """The flagship extraction-honesty case: severity is genuinely
    undetermined from text alone, so the UI must show a clarifying
    question and a conservative-floor Class IIa, not a confident-looking
    Class I. Mirrors tests/test_cli.py::test_cli_text_mode_surfaces_clarifying_questions."""
    at = _fresh_app()
    _classify_via_text_example(at, "Heartbeat monitoring app (clarifying questions)")
    assert at.metric[0].value == "Class IIa"
    assert any("Class IIb" in w.value for w in at.warning)
    assert any("Questions to resolve this classification" in w.value for w in at.warning)


def test_json_example_reaches_expected_class():
    at = _fresh_app()
    _classify_via_json_example(at, "Hip Implant")
    assert at.metric[0].value == "Class III"


def test_all_json_examples_run_without_exception():
    for key in JSON_EXAMPLES:
        at = _fresh_app()
        _classify_via_json_example(at, key)
        assert not at.exception, f"{key!r} raised: {at.exception}"
        assert len(at.metric) == 1


def test_invalid_json_shows_friendly_error_not_a_crash():
    at = _fresh_app()
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.text_area[0].set_value("{not valid json").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Invalid JSON" in e.value for e in at.error)
    assert len(at.metric) == 0


def test_unknown_field_json_shows_friendly_error_not_a_crash():
    at = _fresh_app()
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.text_area[0].set_value('{"not_a_real_field": true}').run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Invalid device attributes" in e.value for e in at.error)


def test_empty_text_input_shows_sidebar_error_not_a_crash():
    at = _fresh_app()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Enter a device description" in e.value for e in at.sidebar.error)
    assert len(at.metric) == 0


def test_successful_classification_renders_rule_breakdown_and_standards_tables():
    at = _fresh_app()
    _classify_via_text_example(at, "Hip replacement implant (Class III)")
    # Two dataframes: the 22-rule breakdown and the 14-category standards mapping.
    assert len(at.dataframe) == 2


def test_empty_json_input_shows_sidebar_error_not_a_crash():
    at = _fresh_app()
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Enter DeviceAttributes JSON" in e.value for e in at.sidebar.error)
    assert len(at.metric) == 0


def test_unexpected_extraction_error_shows_friendly_message_not_a_crash():
    """Defensive net around the pipeline call: even if something inside
    extraction blew up unexpectedly, the app must show a message, not a
    raw traceback, for a public-facing demo."""
    at = _fresh_app()
    at.sidebar.selectbox[0].select("Hip replacement implant (Class III)").run()
    # Patched at its defining module, not "ui.app" - patch()'s string form
    # would import "ui.app" directly to resolve the target, which (like any
    # plain import of a Streamlit script) crashes outside a real session.
    # ui.app.KeywordExtractor is the same class object either way.
    with patch("extraction.keyword_extractor.KeywordExtractor.extract", side_effect=RuntimeError("boom")):
        at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("Could not process this input" in e.value for e in at.error)


def test_undetermined_classification_shows_error_not_a_crash():
    """A real (if minimal) structured input that genuinely leaves every
    Annex VIII rule inapplicable - confirms the UI's UNDETERMINED path,
    not just the classification engine's own None case."""
    at = _fresh_app()
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.text_area[0].set_value('{"invasiveness": "invasive_body_orifice"}').run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert len(at.metric) == 0
    assert any("UNDETERMINED" in e.value for e in at.error)


def test_free_text_with_no_keyword_matches_shows_caption_not_a_crash():
    at = _fresh_app()
    at.sidebar.text_area[0].set_value("asdf jkl qwerty banana").run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert any("No keyword matches found" in c.value for c in at.caption)


def test_ambiguous_rule_flag_shown_for_ancillary_joint_component():
    """Rule 8's still-flagged 'ancillary component' judgement call
    (pedicle screws etc. - see docs/CLARIFICATIONS_RULE_8.md) must
    surface its warning in the rule-breakdown expander."""
    at = _fresh_app()
    at.sidebar.radio[0].set_value("Structured JSON (advanced)").run()
    at.sidebar.text_area[0].set_value(
        '{"is_implantable": true, "is_joint_replacement": true, "is_ancillary_component": true}'
    ).run()
    at.sidebar.button[0].click().run()
    assert not at.exception
    assert at.metric[0].value == "Class IIb"
    assert any("JUDGEMENT CALL FLAGGED" in w.value for w in at.warning)
