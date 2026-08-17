"""The classifier tool itself - a sibling front-end to ``cli.py``, both
sitting on top of the same three core packages (``rules_engine``,
``extraction``, ``standards_mapper``) and knowing nothing about each
other. This file owns layout and input handling only; all display logic
lives in ``ui/render.py``.

Input lives in the main content area, inside a bordered ``st.container``,
not the sidebar - it did originally, but a multi-line description, a
file uploader, and a JSON blob all genuinely need more than a ~300px
sidebar column gives them. The sidebar is left for navigation (which
``st.navigation(position="sidebar")`` populates on its own - see
``ui/app.py``) and the secondary "About this tool" note.

The classification and standards-mapping logic is byte-for-byte
identical to the CLI's - same deterministic engine, same extractor, same
full-transparency principle. Nothing on this page adds to that logic; it
only presents it, and gives free text more ways to arrive (typed,
pasted, extracted from an uploaded document, or OCR'd from an uploaded
image) before it reaches the exact same KeywordExtractor.

This page calls ``inject_scroll_effects()`` too, but only for the top
progress bar (a pure indicator, gates nothing) - deliberately does not
use ``mt-reveal``/``data-count-to`` markup the way ui/pages/home.py
does. Hiding a device's actual classification behind scroll position
would be bad UX for a tool: results should appear complete immediately,
not be gated behind scrolling into view.
"""

from __future__ import annotations

import json

import streamlit as st

from cli import device_attributes_from_dict
from extraction.keyword_extractor import KeywordExtractor
from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from standards_mapper.eu_mdr.mapper import EUMDRStandardsMapper
from ui.examples import JSON_EXAMPLES, TEXT_EXAMPLES
from ui.file_extraction import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    ImageDecodeError,
    TesseractNotAvailableError,
    UnsupportedFileTypeError,
    extract_text_from_upload,
)
from ui.render import (
    DISCLAIMER,
    render_classification_header,
    render_disclaimer,
    render_extraction_section,
    render_rule_breakdown,
    render_standards_mapping,
)
from ui.style import inject_css, inject_scroll_effects

inject_css()
inject_scroll_effects()


def _apply_text_example() -> None:
    choice = st.session_state.text_example_choice
    if choice in TEXT_EXAMPLES:
        st.session_state.device_text = TEXT_EXAMPLES[choice]


def _apply_json_example() -> None:
    choice = st.session_state.json_example_choice
    if choice in JSON_EXAMPLES:
        st.session_state.device_json = JSON_EXAMPLES[choice].read_text(encoding="utf-8")


def _extract_uploaded_files(files: list) -> tuple[dict[str, str], dict[str, str]]:
    """Run every uploaded file through ui.file_extraction. Returns
    (successful text per filename, error message per filename) - a file
    that fails doesn't block the others."""
    extracted: dict[str, str] = {}
    errors: dict[str, str] = {}
    for f in files:
        try:
            text = extract_text_from_upload(f.name, f.getvalue())
        # UnsupportedFileTypeError is unreachable through this page in
        # practice - the file_uploader widget's own `type=` restriction
        # above already blocks any other extension client- and
        # server-side before this code runs. Handled anyway (defence in
        # depth: extract_text_from_upload is also called directly,
        # unguarded, in tests/test_file_extraction.py) rather than
        # trusting the widget alone.
        except (UnsupportedFileTypeError, TesseractNotAvailableError, ImageDecodeError) as exc:
            errors[f.name] = str(exc)
        except Exception as exc:  # defensive: a bad file must never crash the page
            errors[f.name] = f"Could not process this file: {exc}"
        else:
            if text:
                extracted[f.name] = text
            else:
                errors[f.name] = "No text found in this file."
    return extracted, errors


# --- Sidebar: navigation only + secondary info ---

with st.sidebar.expander("About this tool"):
    st.caption(DISCLAIMER)
    st.caption(
        "The classification logic is not an LLM guessing an answer - it's explicit, "
        "unit-tested Python implementing Annex VIII Rules 1-22 against the verbatim text "
        "of Regulation (EU) 2017/745. See the README on GitHub for the full regulatory-"
        "grounding methodology and source citations."
    )

# --- Main area: input ---

st.title("⚕️ Classify a device")
st.caption(
    "A deterministic, auditable EU MDR 2017/745 Annex VIII classification engine — "
    "not an LLM guessing an answer."
)

mode = st.radio(
    "Input mode",
    ["Free text (recommended)", "Structured JSON (advanced)"],
    horizontal=True,
    help=(
        "Free text runs the default keyword extractor first (extraction.KeywordExtractor), "
        "same as the CLI's --text mode. Structured JSON bypasses extraction entirely and feeds "
        "DeviceAttributes straight to the deterministic engine, same as the CLI's default mode."
    ),
)

with st.container(border=True):
    if mode.startswith("Free text"):
        st.selectbox(
            "Try an example",
            ["— choose —"] + list(TEXT_EXAMPLES.keys()),
            key="text_example_choice",
            on_change=_apply_text_example,
        )

        uploaded_files = st.file_uploader(
            "Or upload a document / image",
            type=SUPPORTED_DOCUMENT_EXTENSIONS + SUPPORTED_IMAGE_EXTENSIONS,
            accept_multiple_files=True,
            help=(
                "PDF/DOCX/TXT: text is extracted directly. PNG/JPEG: text visible in the image "
                "(e.g. labels or callouts on a technical drawing) is read via OCR - it cannot "
                "interpret a device's shape or appearance, only text actually printed in the image."
            ),
        )
        if uploaded_files:
            extracted, errors = _extract_uploaded_files(uploaded_files)
            for name, text in extracted.items():
                with st.expander(f"📄 {name}"):
                    st.text(text[:500] + ("…" if len(text) > 500 else ""))
            for name, msg in errors.items():
                st.warning(f"{name}: {msg}")
            if extracted and st.button("Add extracted text to description", width="stretch"):
                existing = st.session_state.get("device_text", "").strip()
                combined = "\n\n".join(([existing] if existing else []) + list(extracted.values()))
                st.session_state.device_text = combined[:2000]

        st.text_area(
            "Device description",
            key="device_text",
            height=220,
            max_chars=2000,
            placeholder=(
                "Describe the device: what it is, what it's made of, where and how it "
                "contacts the body, and whether it's active, software, sterile, or implantable."
            ),
        )
    else:
        st.selectbox(
            "Try an example",
            ["— choose —"] + list(JSON_EXAMPLES.keys()),
            key="json_example_choice",
            on_change=_apply_json_example,
        )
        st.text_area(
            "DeviceAttributes JSON",
            key="device_json",
            height=280,
            placeholder='{\n  "invasiveness": "surgically_invasive",\n  "is_implantable": true\n}',
        )
        st.caption("See rules_engine/models.py for the full DeviceAttributes field reference.")

    col_btn, _ = st.columns([1, 3])
    with col_btn:
        run = st.button("Classify", type="primary", width="stretch")

    if run:
        if mode.startswith("Free text"):
            text = st.session_state.get("device_text", "").strip()
            if not text:
                st.error("Enter a device description first.")
            else:
                st.session_state.pipeline_mode = "text"
                st.session_state.pipeline_input = text
                st.session_state.has_result = True
        else:
            raw = st.session_state.get("device_json", "").strip()
            if not raw:
                st.error("Enter DeviceAttributes JSON first.")
            else:
                st.session_state.pipeline_mode = "json"
                st.session_state.pipeline_input = raw
                st.session_state.has_result = True

st.write("")

# --- Main area: output ---

if not st.session_state.get("has_result"):
    st.info(
        "👆 Describe a device above (or pick an example, or upload a document/image) "
        "and click **Classify** to see a full, auditable EU MDR 2017/745 classification - every "
        "rule and every standards-mapping category checked, not just the ones that applied."
    )
    render_disclaimer()
    st.stop()

extraction = None
device = None
error = None

try:
    if st.session_state.pipeline_mode == "text":
        extraction = KeywordExtractor().extract(st.session_state.pipeline_input)
        device = extraction.device
    else:
        try:
            data = json.loads(st.session_state.pipeline_input)
        except json.JSONDecodeError as exc:
            error = f"Invalid JSON: {exc}"
        else:
            try:
                device = device_attributes_from_dict(data)
            except (ValueError, TypeError) as exc:
                error = f"Invalid device attributes: {exc}"
except Exception as exc:  # defensive: never show a raw traceback for arbitrary user input
    error = f"Could not process this input: {exc}"

if error:
    st.error(error)
    render_disclaimer()
    st.stop()

result = EUMDRClassificationEngine().classify(device)
mapping = EUMDRStandardsMapper().map(device, result)

if device.name or device.description:
    st.subheader(device.name or "(unnamed device)")
    if device.description:
        st.caption(device.description)

render_classification_header(result)
st.divider()

if extraction is not None:
    render_extraction_section(extraction)
    st.divider()

render_rule_breakdown(result)
st.divider()
render_standards_mapping(mapping)

render_disclaimer()
