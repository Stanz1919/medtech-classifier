"""End-to-end tests: free text -> KeywordExtractor -> EUMDRClassificationEngine.

These test the FULL Phase 2 pipeline for specific, hand-picked
descriptions where the keyword extractor's documented coverage is
sufficient to reach the correct classification - they are not a claim
that the extractor reliably handles arbitrary text (see
extraction/keyword_extractor.py's module docstring for known scope
limits, and tests/test_extraction.py::test_placed_in_teeth_infers_implantable_but_not_invasiveness
for a documented residual gap).

Several of these mirror ground-truth cases already covered directly
against DeviceAttributes in tests/test_known_devices.py - repeating them
here as free text confirms the extraction layer feeds the rules engine
correctly, not just that the rules engine itself is correct.
"""

from __future__ import annotations

import pytest

from extraction.keyword_extractor import KeywordExtractor
from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from rules_engine.models import DeviceClass

CASES = [
    (
        "Hypodermic syringe",
        "A sterile, single-use hypodermic syringe used to inject medicinal products under the skin.",
        DeviceClass.IIA,
    ),
    (
        "Hip replacement implant",
        "A titanium hip replacement implant intended for permanent placement in the joint.",
        DeviceClass.III,
    ),
    (
        "Cardiac pacemaker",
        "A cardiac pacemaker implanted permanently to regulate heart rhythm.",
        DeviceClass.III,
    ),
    (
        "Hydrogel wound dressing managing micro-environment",
        "A hydrogel wound dressing intended to manage the micro-environment of a wound that has not breached the dermis.",
        DeviceClass.IIA,
    ),
    (
        "Simple gauze dressing",
        "A gauze dressing that acts as a mechanical barrier and absorbs exudate from a wound.",
        DeviceClass.I,
    ),
    (
        "Condom with spermicide",
        "A condom coated with spermicide for contraception.",
        DeviceClass.III,  # Rule 14 (ancillary medicinal substance) overrides Rule 15's IIb
    ),
    (
        "Porcine collagen wound dressing",
        "A porcine-derived collagen dressing intended for wound care.",
        DeviceClass.III,  # Rule 18: animal tissue, not intact-skin-only (wound contact)
    ),
    (
        "Dental filling",
        "A composite dental filling material placed within the tooth to restore a cavity.",
        DeviceClass.IIA,
    ),
    (
        "Breast implant",
        "A silicone breast implant intended for permanent placement.",
        DeviceClass.III,
    ),
    (
        "Reusable surgical scissors",
        "A reusable surgical instrument used briefly during a single procedure to cut tissue.",
        DeviceClass.I,
    ),
    (
        "Sterile wound dressing",
        "A sterile gauze dressing that acts as a mechanical barrier for a minor wound.",
        DeviceClass.I,
    ),
    (
        "Drug-eluting coronary stent",
        "A drug-eluting stent implanted in direct contact with the heart.",
        DeviceClass.III,
    ),
]


@pytest.mark.parametrize("name,text,expected_class", CASES, ids=[c[0] for c in CASES])
def test_text_to_classification_pipeline(name, text, expected_class):
    extraction = KeywordExtractor().extract(text)
    result = EUMDRClassificationEngine().classify(extraction.device)
    assert result.device_class == expected_class, (
        f"{name}: expected Class {expected_class.value}, got "
        f"{result.device_class.value if result.device_class else None}. "
        f"Text: {text!r}. Matched signals: {extraction.matched_signals}. "
        f"Unmatched notes: {extraction.unmatched_notes}."
    )


def test_reusable_surgical_instrument_reaches_class_i_via_rule_6_not_rule_1():
    """Regression test: this case's Class I result must come from Rule 6's
    actual reusable-surgical-instrument exception, not an accidental Rule
    1 fallback caused by invasiveness never being inferred. Fixed by
    grounding the surgical-invasiveness keyword list in Annex VIII 2.3's
    own defining vocabulary ("cutting, drilling, sawing, scratching,
    scraping, clamping, retracting, clipping")."""
    text = "A reusable surgical instrument used briefly during a single procedure to cut tissue."
    extraction = KeywordExtractor().extract(text)
    assert extraction.device.invasiveness.value == "surgically_invasive"
    assert extraction.device.duration.value == "transient"
    result = EUMDRClassificationEngine().classify(extraction.device)
    assert result.device_class == DeviceClass.I
    deciding_rules = {o.rule_id for o in result.triggered_rules if o.device_class == result.device_class}
    assert deciding_rules == {"Rule 6"}


def test_dental_filling_reaches_class_iia_via_rule_8_not_rule_1():
    """This was originally a documented gap: "dental filling" set
    placed_in_teeth but never invasiveness, so Rule 8's gate
    (is_implantable OR long-term surgically invasive) never fired and
    the description silently fell through to Rule 1's non-invasive
    default - reaching IIa by accident-adjacent means, not because Rule
    8's "placed in the teeth" exception actually applied.

    Fixed: the extractor now infers is_implantable=True whenever a
    genuine intra-tooth placement signal fires (fillings/crowns/bridges
    remain in place via clinical intervention, matching Article 2(5)'s
    implantable definition even though they aren't colloquially called
    "implants" - see docs/CLARIFICATIONS_RULE_8.md). This test confirms
    Rule 8 is now the ACTUAL deciding rule, for the right reason, even
    though invasiveness itself still isn't separately inferred for this
    phrasing."""
    text = "A composite dental filling material placed within the tooth to restore a cavity."
    extraction = KeywordExtractor().extract(text)
    assert extraction.device.placed_in_teeth is True
    assert extraction.device.is_implantable is True  # inferred alongside placed_in_teeth
    result = EUMDRClassificationEngine().classify(extraction.device)
    assert result.device_class == DeviceClass.IIA
    deciding_rules = {o.rule_id for o in result.triggered_rules if o.device_class == result.device_class}
    assert deciding_rules == {"Rule 8"}
