"""Smoke tests for the Streamlit UI (ui/app.py's router and its pages),
using Streamlit's own streamlit.testing.v1.AppTest harness - it runs the
real page script in a simulated session and lets us assert on the
resulting widget tree, rather than needing a browser.

Each page is tested by pointing AppTest directly at its file
(ui/pages/classify.py, ui/pages/home.py) rather than at the ui/app.py
router - AppTest runs one script at a time, and a page script behaves
identically whether it was reached via st.navigation or run standalone
(neither page calls st.set_page_config, which lives solely in the
router - see ui/app.py's module docstring).

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

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
CLASSIFY_PAGE_PATH = str(UI_DIR / "pages" / "classify.py")
HOME_PAGE_PATH = str(UI_DIR / "pages" / "home.py")


def _fresh_app() -> AppTest:
    at = AppTest.from_file(CLASSIFY_PAGE_PATH)
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


# --- Router / navigation (ui/app.py) ---
# Tested by pointing AppTest at the router itself, not at a page in
# isolation: st.switch_page() resolves paths relative to the "main
# script," which only exists correctly when the router is the entry
# point - see this file's module docstring.


def test_router_shows_home_page_by_default():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "ui" / "app.py"))
    at.run()
    assert not at.exception
    assert any("Start classifying" in b.label for b in at.button)


def test_router_start_classifying_button_navigates_to_classify_page():
    at = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "ui" / "app.py"))
    at.run()
    at.button[0].click().run()
    assert not at.exception
    assert any(t.value == "⚕️ Classify a device" for t in at.title)


# --- Home page content (standalone) ---


def _fresh_home() -> AppTest:
    at = AppTest.from_file(HOME_PAGE_PATH)
    at.run()
    assert not at.exception, f"Home page raised on load: {at.exception}"
    return at


def test_home_page_loads_without_exception_and_has_cta():
    at = _fresh_home()
    assert any("Start classifying" in b.label for b in at.button)


def test_home_page_shows_all_four_risk_classes():
    at = _fresh_home()
    badge_values = [b.label for b in at.get("badge")] if at.get("badge") else []
    # st.badge elements aren't exposed under a dedicated at.badge accessor
    # in this Streamlit version - fall back to full page markdown text.
    text = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    for cls in ["Class I", "Class IIa", "Class IIb", "Class III"]:
        assert cls in text or cls in str(badge_values)


def test_home_page_shows_disclaimer():
    at = _fresh_home()
    assert any("not real regulatory or legal advice" in c.value for c in at.caption)


def test_home_page_stat_strip_has_correct_real_numbers():
    """AppTest can't verify the count-up animation (that needs a real,
    compositing browser - see ui/style.py's module docstring for why),
    but it can verify the right numbers actually got injected, which is
    what the animation would be counting up to."""
    at = _fresh_home()
    full_markup = " ".join(m.value for m in at.markdown)
    assert 'data-count-to="22"' in full_markup
    assert 'data-count-to="14"' in full_markup
    assert 'data-count-to="349"' in full_markup
    assert 'data-count-to="100" data-count-suffix="%"' in full_markup


def test_home_page_subnav_links_match_real_section_ids():
    at = _fresh_home()
    full_markup = " ".join(m.value for m in at.markdown)
    for anchor_id, link_target in [("mt-why", "#mt-why"), ("mt-how", "#mt-how"), ("mt-ladder", "#mt-ladder")]:
        assert f'id="{anchor_id}"' in full_markup, f"missing section id={anchor_id!r}"
        assert f'href="{link_target}"' in full_markup, f"subnav missing link to {link_target!r}"


def test_home_page_hero_and_cards_are_wired_for_scroll_reveal():
    at = _fresh_home()
    full_markup = " ".join(m.value for m in at.markdown)
    assert 'class="mt-stats mt-reveal"' in full_markup
    assert full_markup.count('mt-card mt-reveal') == 7  # 4 feature cards + 3 how-it-works steps


# --- Document / image upload wiring (ui/pages/classify.py) ---


def _make_docx_bytes(text: str) -> bytes:
    import io

    import docx

    d = docx.Document()
    d.add_paragraph(text)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _make_ocr_image_bytes(text: str) -> bytes:
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (600, 120), color="white")
    ImageDraw.Draw(img).text((10, 40), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_uploaded_txt_document_previews_and_populates_description():
    at = _fresh_app()
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload("spec.txt", b"A titanium hip replacement implant intended for permanent placement.").run()
    assert not at.exception
    # Preview shown before the user opts to add it to the description.
    assert any("spec.txt" in e.label for e in at.sidebar.expander)
    add_button = next(b for b in at.sidebar.button if "Add extracted text" in b.label)
    add_button.click().run()
    assert "hip replacement implant" in at.sidebar.text_area[0].value.lower()
    at.sidebar.button[-1].click().run()  # Classify
    assert not at.exception
    assert at.metric[0].value == "Class III"


def test_uploaded_docx_document_reaches_expected_class():
    at = _fresh_app()
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload(
        "spec.docx",
        _make_docx_bytes("A cardiac pacemaker implanted permanently to regulate heart rhythm."),
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ).run()
    add_button = next(b for b in at.sidebar.button if "Add extracted text" in b.label)
    add_button.click().run()
    at.sidebar.button[-1].click().run()
    assert not at.exception
    assert at.metric[0].value == "Class III"


def test_uploaded_image_is_ocrd_and_reaches_expected_class():
    """Real Tesseract OCR through the full UI wiring, not mocked - see
    tests/test_file_extraction.py for the module-level OCR tests."""
    at = _fresh_app()
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload("drawing.png", _make_ocr_image_bytes("Implantable cardiac pacemaker"), mime_type="image/png").run()
    assert not at.exception
    add_button = next(b for b in at.sidebar.button if "Add extracted text" in b.label)
    add_button.click().run()
    assert "pacemaker" in at.sidebar.text_area[0].value.lower()
    at.sidebar.button[-1].click().run()
    assert not at.exception
    assert at.metric[0].value == "Class III"


def test_uploaded_image_with_no_visible_text_shows_no_text_found_warning():
    """Honest degradation, not a crash or a guess: OCR on an image with
    nothing printed on it must say so plainly (see ui/file_extraction.py's
    module docstring on why this tool won't try to interpret a bare
    photo's shape/appearance)."""
    import io

    from PIL import Image

    at = _fresh_app()
    blank = Image.new("RGB", (200, 200), color="white")
    buf = io.BytesIO()
    blank.save(buf, format="PNG")
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload("device_photo.png", buf.getvalue(), mime_type="image/png").run()
    assert not at.exception
    assert any("No text found" in w.value for w in at.sidebar.warning)
    assert not any("Add extracted text" in b.label for b in at.sidebar.button)


def test_uploaded_image_when_tesseract_unavailable_shows_friendly_warning():
    """Patched at ui.file_extraction's own pytesseract import, not at
    ui.pages.classify - patch()'s string form would import the page
    directly to resolve the target, which (like any plain import of a
    Streamlit script) crashes outside a real session. Same reasoning as
    tests/test_ui.py's KeywordExtractor mock from the Phase 4 suite."""
    import pytesseract

    at = _fresh_app()
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload("drawing.png", _make_ocr_image_bytes("Implantable cardiac pacemaker"), mime_type="image/png").run()
    with patch.object(pytesseract, "image_to_string", side_effect=pytesseract.TesseractNotFoundError()):
        at.run()
    assert not at.exception
    assert any("OCR isn't available" in w.value for w in at.sidebar.warning)
    assert not any("Add extracted text" in b.label for b in at.sidebar.button)


def test_uploaded_corrupt_image_shows_warning_not_a_crash():
    """A validly-named .png that isn't actually a decodable image - the
    one upload-time failure the file_uploader widget's own `type=`
    restriction can't prevent (unlike a wrong extension, which Streamlit
    itself blocks before this app's code ever runs - see
    tests/test_file_extraction.py::test_extract_text_from_upload_rejects_unsupported_extension
    for that defensive path instead)."""
    at = _fresh_app()
    uploader = at.sidebar.get("file_uploader")[0]
    uploader.upload("drawing.png", b"not actually a png file", mime_type="image/png").run()
    assert not at.exception
    assert any("drawing.png" in w.value for w in at.sidebar.warning)
    assert not any("Add extracted text" in b.label for b in at.sidebar.button)
