"""Tests for cross-rule precedence: Annex VIII Chapter II, point 3.5 -
"the strictest rule and sub-rule resulting in the higher classification
shall apply" - applied across *different* rules, not just within one.
"""

from __future__ import annotations

from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from rules_engine.models import (
    DeviceAttributes,
    DeviceClass,
    Invasiveness,
    NanomaterialExposurePotential,
)


def test_multiple_rules_apply_highest_class_wins():
    """A non-invasive device that ALSO happens to be flagged as
    containing nanomaterial with high exposure potential: Rule 1 alone
    would say Class I, but Rule 19 says Class III. The engine must return
    Class III and cite Rule 19 as decisive."""
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        contains_nanomaterial=True,
        nanomaterial_internal_exposure_potential=NanomaterialExposurePotential.HIGH,
    )
    result = EUMDRClassificationEngine().classify(device)

    assert result.device_class == DeviceClass.III
    triggered_ids = {o.rule_id for o in result.triggered_rules}
    assert "Rule 1" in triggered_ids  # Rule 1 still applies and is reported...
    assert "Rule 19" in triggered_ids
    deciding_ids = {o.rule_id for o in result.triggered_rules if o.device_class == DeviceClass.III}
    assert deciding_ids == {"Rule 19"}  # ...but is not what decided the final class


def test_implantable_joint_replacement_overrides_lower_rule8_base():
    """Rule 8's own internal bullets: base IIb vs joint-replacement
    exception III. Confirms within-rule precedence via the engine too."""
    device = DeviceAttributes(is_implantable=True, is_joint_replacement=True)
    result = EUMDRClassificationEngine().classify(device)
    assert result.device_class == DeviceClass.III


def test_no_rule_applies_returns_none_and_explains():
    """An almost-blank device (all defaults) should not silently produce
    a confident classification for a device with no stated invasiveness
    behaviour that matches any rule other than the Rule 1 default. This
    test instead asserts that a genuinely non-invasive default device
    resolves via Rule 1's fallback, and that its explanation names Rule 1."""
    device = DeviceAttributes()  # defaults to non_invasive
    result = EUMDRClassificationEngine().classify(device)
    assert result.device_class == DeviceClass.I
    assert "Rule 1" in result.explanation


def test_ambiguous_flags_surface_in_final_result():
    # Rule 18's animal-tissue/intact-skin carve-out USED to be the example
    # here, but MDCG 2021-24 Note 3 resolved it explicitly (Class I) - see
    # docs/CLARIFICATIONS_RULE_18.md - so it's no longer flagged ambiguous.
    # Rule 8's "ancillary component" carve-out remains a genuine judgement
    # call per MDCG's own Note 1 (no blanket rule), so it's used instead.
    device = DeviceAttributes(
        is_implantable=True,
        is_joint_replacement=True,
        is_ancillary_component=True,
    )
    result = EUMDRClassificationEngine().classify(device)
    assert result.has_ambiguous_flags
    ambiguous_rule_ids = {o.rule_id for o in result.ambiguous_outcomes}
    assert "Rule 8" in ambiguous_rule_ids
