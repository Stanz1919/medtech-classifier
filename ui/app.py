"""Streamlit UI for the MedTech Device Regulatory Classifier.

A sibling front-end to ``cli.py`` - both sit on top of the same three
core packages (``rules_engine``, ``extraction``, ``standards_mapper``)
and know nothing about each other. This file owns layout and input
handling only; all display logic lives in ``ui/render.py``.

Run locally:
    streamlit run ui/app.py

The classification and standards-mapping logic is byte-for-byte
identical to the CLI's - same deterministic engine, same extractor,
same full-transparency principle (every rule and every GSPR category is
always shown, not just the ones that apply). This file adds nothing to
that logic; it only presents it.
"""

from __future__ import annotations

import json

import streamlit as st

from cli import device_attributes_from_dict
from extraction.keyword_extractor import KeywordExtractor
from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from standards_mapper.eu_mdr.mapper import EUMDRStandardsMapper
from ui.examples import JSON_EXAMPLES, TEXT_EXAMPLES
from ui.render import (
    DISCLAIMER,
    render_classification_header,
    render_disclaimer,
    render_extraction_section,
    render_rule_breakdown,
    render_standards_mapping,
)

st.set_page_config(
    page_title="MedTech Device Regulatory Classifier",
    page_icon="⚕️",
    layout="wide",
)


def _apply_text_example() -> None:
    choice = st.session_state.text_example_choice
    if choice in TEXT_EXAMPLES:
        st.session_state.device_text = TEXT_EXAMPLES[choice]


def _apply_json_example() -> None:
    choice = st.session_state.json_example_choice
    if choice in JSON_EXAMPLES:
        st.session_state.device_json = JSON_EXAMPLES[choice].read_text(encoding="utf-8")


# --- Sidebar: input ---

st.sidebar.title("⚕️ Classify a device")
mode = st.sidebar.radio(
    "Input mode",
    ["Free text (recommended)", "Structured JSON (advanced)"],
    help=(
        "Free text runs the default keyword extractor first (extraction.KeywordExtractor), "
        "same as the CLI's --text mode. Structured JSON bypasses extraction entirely and feeds "
        "DeviceAttributes straight to the deterministic engine, same as the CLI's default mode."
    ),
)

if mode.startswith("Free text"):
    st.sidebar.selectbox(
        "Try an example",
        ["— choose —"] + list(TEXT_EXAMPLES.keys()),
        key="text_example_choice",
        on_change=_apply_text_example,
    )
    st.sidebar.text_area(
        "Device description",
        key="device_text",
        height=160,
        max_chars=2000,
        placeholder=(
            "Describe the device: what it is, what it's made of, where and how it "
            "contacts the body, and whether it's active, software, sterile, or implantable."
        ),
    )
else:
    st.sidebar.selectbox(
        "Try an example",
        ["— choose —"] + list(JSON_EXAMPLES.keys()),
        key="json_example_choice",
        on_change=_apply_json_example,
    )
    st.sidebar.text_area(
        "DeviceAttributes JSON",
        key="device_json",
        height=240,
        placeholder='{\n  "invasiveness": "surgically_invasive",\n  "is_implantable": true\n}',
    )
    st.sidebar.caption("See rules_engine/models.py for the full DeviceAttributes field reference.")

run = st.sidebar.button("Classify", type="primary", width="stretch")

if run:
    if mode.startswith("Free text"):
        text = st.session_state.get("device_text", "").strip()
        if not text:
            st.sidebar.error("Enter a device description first.")
        else:
            st.session_state.pipeline_mode = "text"
            st.session_state.pipeline_input = text
            st.session_state.has_result = True
    else:
        raw = st.session_state.get("device_json", "").strip()
        if not raw:
            st.sidebar.error("Enter DeviceAttributes JSON first.")
        else:
            st.session_state.pipeline_mode = "json"
            st.session_state.pipeline_input = raw
            st.session_state.has_result = True

st.sidebar.divider()
with st.sidebar.expander("About this tool"):
    st.caption(DISCLAIMER)
    st.caption(
        "The classification logic is not an LLM guessing an answer - it's explicit, "
        "unit-tested Python implementing Annex VIII Rules 1-22 against the verbatim text "
        "of Regulation (EU) 2017/745. See the README on GitHub for the full regulatory-"
        "grounding methodology and source citations."
    )

# --- Main area: output ---

st.title("⚕️ MedTech Device Regulatory Classifier")
st.caption(
    "A deterministic, auditable EU MDR 2017/745 Annex VIII classification engine — "
    "not an LLM guessing an answer."
)

if not st.session_state.get("has_result"):
    st.info(
        "👈 Describe a device in the sidebar (or pick an example) and click **Classify** "
        "to see a full, auditable EU MDR 2017/745 classification - every rule and every "
        "standards-mapping category checked, not just the ones that applied."
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
