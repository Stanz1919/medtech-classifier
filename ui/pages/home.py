"""Homepage: what this tool is, why it's built the way it is, and how to
use it - before the visitor ever sees the classifier's input controls.
Pure explainer content; no classification logic lives here at all.
"""

from __future__ import annotations

import streamlit as st

from ui.render import DISCLAIMER, render_disclaimer
from ui.style import inject_css

inject_css()

st.markdown(
    """
    <div class="mt-hero">
        <div class="mt-eyebrow">EU MDR 2017/745 · ANNEX VIII</div>
        <h1>Know your device's risk class —<br/>and exactly <span class="mt-accent">why</span>.</h1>
        <p class="mt-tagline">
            A deterministic, auditable classification engine built directly against the
            verbatim text of Regulation (EU) 2017/745. Not an LLM guessing an answer -
            explicit, unit-tested Python implementing all 22 Annex VIII rules, citing
            exactly which one(s) triggered your result.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, _ = st.columns([1, 1, 2])
with col1:
    if st.button("Start classifying →", type="primary", width="stretch"):
        st.switch_page("pages/classify.py")
with col2:
    st.link_button("View source on GitHub", "https://github.com/Stanz1919/medtech-classifier", width="stretch")

st.write("")
st.markdown('<div class="mt-section-title">Why this is different</div>', unsafe_allow_html=True)

_FEATURES = [
    (
        "Deterministic, not probabilistic",
        "The same device attributes always produce the same class, through the same "
        "named rule(s) - no sampling, no temperature, nothing to re-roll.",
    ),
    (
        "Grounded in the actual regulation",
        "Every citation traces back to verbatim text fetched from EUR-Lex and MDCG "
        "guidance, saved in docs/legal_sources/ - never reconstructed from memory.",
    ),
    (
        "Full transparency by default",
        "Every one of the 22 Annex VIII rules and 14 standards-mapping categories is "
        "shown, not just the ones that applied - a Class I result visibly means "
        "\"we checked everything,\" never a silent absence of information.",
    ),
    (
        "Honest about its own limits",
        "Where the extractor genuinely can't determine something from your text, it "
        "asks a specific clarifying question instead of quietly guessing - see the "
        "heartbeat-monitoring-app example on the Classify page.",
    ),
]
cols = st.columns(4)
for col, (title, body) in zip(cols, _FEATURES):
    with col:
        st.markdown(f'<div class="mt-card"><h3>{title}</h3><p>{body}</p></div>', unsafe_allow_html=True)

st.write("")
st.markdown('<div class="mt-section-title">How it works</div>', unsafe_allow_html=True)

_STEPS = [
    (
        "Describe the device",
        "Type a description, pick a worked example, or upload a document/technical "
        "drawing/photo - text is extracted or OCR'd, never interpreted by a model.",
    ),
    (
        "Deterministic classification",
        "The description runs through the keyword extractor, then all 22 Annex VIII "
        "rules are evaluated in full against Annex VIII Chapter II 3.5's precedence "
        "principle.",
    ),
    (
        "Full audit trail",
        "See exactly which rule(s) decided the result, every rule that didn't apply "
        "and why, and which of the 14 GSPR categories your device needs to satisfy.",
    ),
]
cols = st.columns(3)
for i, (col, (title, body)) in enumerate(zip(cols, _STEPS), start=1):
    with col:
        st.markdown(
            f'<div class="mt-card"><div class="mt-step-num">{i}</div><h3>{title}</h3><p>{body}</p></div>',
            unsafe_allow_html=True,
        )

st.write("")
st.markdown('<div class="mt-section-title">The risk ladder</div>', unsafe_allow_html=True)
st.caption("Annex VIII classifies every device into one of four classes, lowest to highest risk.")

ladder_cols = st.columns(4)
_LADDER = [
    ("I", "green", "Lowest risk", "e.g. a simple wound dressing, a reusable surgical instrument"),
    ("IIa", "yellow", "Low-medium risk", "e.g. a hypodermic syringe, a dental filling"),
    ("IIb", "orange", "Medium-high risk", "e.g. an ancillary joint-implant component, an infusion pump"),
    ("III", "red", "Highest risk", "e.g. a hip implant, a cardiac pacemaker, a coronary stent"),
]
for col, (cls, color, label, example) in zip(ladder_cols, _LADDER):
    with col:
        st.badge(f"Class {cls}", color=color)
        st.caption(f"**{label}**  \n{example}")

st.write("")
render_disclaimer()
