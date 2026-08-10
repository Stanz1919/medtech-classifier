"""Streamlit rendering helpers for the classification pipeline's output.

Pure display functions - each takes one of the core dataclasses
(``ClassificationResult``, ``ExtractionResult``, ``StandardsMappingResult``)
already produced by the core packages and renders it. Deliberately
independent of ``cli.py``: this module and ``cli.py`` are sibling
front-ends over the same three core packages (``rules_engine``,
``extraction``, ``standards_mapper``), not dependent on each other -
matching the project's jurisdiction-agnostic interface pattern
(``ClassificationEngine`` / ``Extractor`` / ``StandardsMapper``). Neither
front-end knows the other exists.

Same full-transparency principle as the CLI report: every rule and every
GSPR category is always shown, not just the ones that applied - just
laid out for a browser instead of a scrolling terminal (compact
table/summary by default, full rationale and citations one click away
in an expander, rather than one long unbroken dump of text).
"""

from __future__ import annotations

import streamlit as st

from extraction.base import ExtractionResult
from rules_engine.models import ClassificationResult, DeviceClass
from standards_mapper.base import StandardsMappingResult

DISCLAIMER = (
    "This is an educational/demonstration tool, not real regulatory or legal advice. "
    "Always consult a notified body / regulatory professional for an actual device classification."
)

# Native st.badge colors ("red"/"orange"/"yellow"/"green"/...) - theme-aware
# out of the box in both light and dark mode, so the headline result never
# risks a hand-rolled color looking wrong under a theme this app didn't
# anticipate. Chosen to read as an actual risk ladder low -> high.
_CLASS_BADGE_COLOR = {
    DeviceClass.I: "green",
    DeviceClass.IIA: "yellow",
    DeviceClass.IIB: "orange",
    DeviceClass.III: "red",
}

_CLASS_RISK_LABEL = {
    DeviceClass.I: "Lowest risk",
    DeviceClass.IIA: "Low-medium risk",
    DeviceClass.IIB: "Medium-high risk",
    DeviceClass.III: "Highest risk",
}


def render_classification_header(result: ClassificationResult) -> None:
    """The headline result: predicted class, qualifiers, and the
    engine's own explanation of which rule(s) decided it."""
    if result.device_class is None:
        st.error(
            "UNDETERMINED - no Annex VIII rule matched the given attributes. "
            "This usually means the device attributes are too sparse; Rule 1 "
            "(non-invasive) or Rule 13 (other active devices) should catch "
            "most fully-specified devices."
        )
        return

    col1, col2 = st.columns([2, 3])
    with col1:
        st.metric("Predicted classification", f"Class {result.device_class.value}")
        st.badge(_CLASS_RISK_LABEL[result.device_class], color=_CLASS_BADGE_COLOR[result.device_class])
        for q in result.qualifiers:
            st.badge(q.value, color="violet")
    with col2:
        st.markdown("**Why:**")
        st.markdown(result.explanation)


def render_extraction_section(extraction: ExtractionResult) -> None:
    """Extraction reasoning: what text drove which conclusion, what
    couldn't be determined, and any genuine judgement calls the user
    needs to resolve - the three-tier honesty structure from
    ``ExtractionResult``, most-actionable (clarifying questions) shown
    most prominently."""
    st.markdown("#### Extraction reasoning (from your free-text description)")

    if extraction.matched_signals:
        st.markdown("**Matched signals** - what in your text drove each conclusion:")
        st.markdown("\n".join(f"- {s}" for s in extraction.matched_signals))
    else:
        st.caption("No keyword matches found in the given text - the classification below rests entirely on defaults.")

    if extraction.unmatched_notes:
        lines = ["**Could not determine - verify these manually before trusting the result:**", ""]
        lines += [f"- {n}" for n in extraction.unmatched_notes]
        st.info("\n".join(lines))

    if extraction.clarifying_questions:
        lines = ["**Questions to resolve this classification:**", ""]
        lines += [f"{i}. {q}" for i, q in enumerate(extraction.clarifying_questions, start=1)]
        st.warning("\n".join(lines))


def render_rule_breakdown(result: ClassificationResult) -> None:
    """Full audit trail: all 22 Annex VIII rules, not just the deciding
    one - a Class I result should visibly mean "we checked everything
    and only Rule 1's default applied," never a silent absence of
    information."""
    st.markdown("#### Full rule-by-rule breakdown (all 22 Annex VIII rules evaluated)")

    decisive_ids = {o.rule_id for o in result.triggered_rules if o.device_class == result.device_class}
    rows = []
    for outcome in result.all_rule_outcomes:
        if outcome.applies and outcome.device_class is not None:
            status = "✅ Decisive" if outcome.rule_id in decisive_ids else "\U0001f539 Triggered, not decisive"
            cls = f"Class {outcome.device_class.value}"
        else:
            status = "⬜ Not applicable"
            cls = "–"
        rows.append({"Rule": outcome.rule_id, "Status": status, "Class": cls, "Rationale": outcome.rationale})

    st.dataframe(rows, hide_index=True, width="stretch")

    with st.expander("Full rationale and source citation for every rule"):
        for outcome in result.all_rule_outcomes:
            st.markdown(f"**{outcome.rule_id}** — {outcome.rationale}")
            st.caption(outcome.source_citation)
            if outcome.ambiguous:
                st.warning(f"JUDGEMENT CALL FLAGGED: {outcome.ambiguous_note}")


def render_standards_mapping(mapping: StandardsMappingResult) -> None:
    """All 14 GSPR categories the classified device was checked
    against, and the standard(s) commonly used to demonstrate
    conformity with each - see standards_mapper/base.py for why these
    are named as "commonly used" rather than asserted to be formally
    EU-harmonised."""
    st.markdown("#### Standards mapping (all GSPR categories checked against the classified device)")
    st.caption(
        "Standards named below are commonly used to demonstrate conformity with a "
        "requirement - not asserted to be the legally mandated choice or currently "
        "EU-harmonised under Article 8. Always verify independently."
    )

    rows = []
    for req in mapping.all_requirements:
        std_names = ", ".join(s.standard_id for s in req.standards)
        rows.append(
            {
                "GSPR category": req.title,
                "Applies": "✅ Yes" if req.applies else "⬜ No",
                "Standard(s)": std_names if std_names else "–",
            }
        )
    st.dataframe(rows, hide_index=True, width="stretch")

    with st.expander("Full rationale, citation and limitations for every category"):
        for req in mapping.all_requirements:
            st.markdown(f"**{req.title}** ({req.source_citation})")
            st.markdown(req.rationale)
            for s in req.standards:
                note = f" — {s.note}" if s.note else ""
                st.markdown(f"- `{s.standard_id}`: {s.title}{note}")
            if req.limitation_note:
                st.caption(f"Limitation: {req.limitation_note}")
            st.divider()


def render_disclaimer() -> None:
    st.divider()
    st.caption(DISCLAIMER)
