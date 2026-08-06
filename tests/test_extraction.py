"""Unit tests for extraction.KeywordExtractor, field group by field group.

Mirrors the style of tests/test_rules_individual.py: each test isolates
one signal group so a failure points at exactly which keyword mapping
broke. See extraction/keyword_extractor.py's module docstring for the
documented scope (what this extractor does and does not attempt).
"""

from __future__ import annotations

from extraction.keyword_extractor import KeywordExtractor
from rules_engine.models import (
    ActiveDeviceType,
    Duration,
    Invasiveness,
    TissueOrigin,
    WoundContactPurpose,
)


def _extract(text):
    return KeywordExtractor().extract(text)


# --- Invasiveness ---


def test_invasiveness_body_orifice_priority_over_generic_surgical_words():
    """A urinary catheter should resolve to INVASIVE_BODY_ORIFICE even
    though "catheter" alone is in the surgical-signal list - the more
    specific orifice phrase must win."""
    result = _extract("A urinary catheter inserted through the urethra.")
    assert result.device.invasiveness == Invasiveness.INVASIVE_BODY_ORIFICE


def test_invasiveness_surgically_invasive():
    result = _extract("A titanium bone screw surgically inserted during hip surgery.")
    assert result.device.invasiveness == Invasiveness.SURGICALLY_INVASIVE


def test_invasiveness_non_invasive_explicit():
    result = _extract("A non-invasive external blood pressure cuff.")
    assert result.device.invasiveness == Invasiveness.NON_INVASIVE


def test_invasiveness_defaults_with_note_when_no_signal():
    result = _extract("A generic medical accessory of some kind.")
    assert result.device.invasiveness == Invasiveness.NON_INVASIVE
    assert any("invasiveness" in note for note in result.unmatched_notes)


# --- Duration ---


def test_duration_transient():
    result = _extract("A single-use device intended for use in a single procedure.")
    assert result.device.duration == Duration.TRANSIENT


def test_duration_long_term():
    result = _extract("A device intended for permanent placement in the body.")
    assert result.device.duration == Duration.LONG_TERM


def test_duration_short_term():
    result = _extract("A device intended to remain in place for several days.")
    assert result.device.duration == Duration.SHORT_TERM


def test_duration_transient_takes_priority_over_short_term_phrasing():
    """"Single-use" (transient) should win even alongside vaguer duration
    language, since it's checked first."""
    result = _extract("A single-use device used briefly during a procedure lasting several days of hospital stay.")
    assert result.device.duration == Duration.TRANSIENT


# --- Active / software ---


def test_is_active_and_therapeutic_type():
    result = _extract("A battery-powered device that delivers therapy to treat chronic pain.")
    assert result.device.is_active is True
    assert result.device.active_type == ActiveDeviceType.THERAPEUTIC


def test_is_active_and_diagnostic_type():
    result = _extract("An electronic device that monitors and measures vital signs.")
    assert result.device.is_active is True
    assert result.device.active_type == ActiveDeviceType.DIAGNOSTIC_MONITORING


def test_is_active_other_active_fallback_with_note():
    result = _extract("An electric wheelchair.")
    assert result.device.is_active is True
    assert result.device.active_type == ActiveDeviceType.OTHER_ACTIVE
    assert any("active_type" in note for note in result.unmatched_notes)


def test_software_with_no_decision_or_monitoring_function_stays_other_software():
    result = _extract("A software application for tracking patient appointments.")
    assert result.device.is_software is True
    # No decision-support or monitoring function detected -> genuinely
    # "all other software" (Rule 11 -> Class I), noted as such.
    assert any("Rule 11" in note for note in result.unmatched_notes)
    assert result.device.software_decision_impact.value == "not_applicable"


def test_software_decision_support_detected_sets_conservative_floor_and_asks_question():
    """Regression test for the bug where decision-support software with
    unknown severity silently fell into the "all other software" (Class
    I) bucket - identical to a pure utility app. Detected function must
    now set at least the IIa floor (SoftwareDecisionImpact.OTHER_IMPACT)
    and raise a clarifying question naming what would change the result."""
    result = _extract("A mobile app that analyses a patient heartbeat, detects abnormalities, and informs a physician.")
    assert result.device.is_software is True
    assert result.device.software_decision_impact.value == "other_impact"
    assert len(result.clarifying_questions) == 1
    assert "Class IIa" in result.clarifying_questions[0]
    assert "Class IIb" in result.clarifying_questions[0]
    assert "Class III" in result.clarifying_questions[0]


def test_software_decision_support_with_death_severity_signal():
    result = _extract("Software that diagnoses stroke and informs a physician of the results.")
    assert result.device.software_decision_impact.value == "death_or_irreversible_deterioration"
    assert result.clarifying_questions == []  # severity was determined, no open question


def test_software_decision_support_with_serious_severity_signal():
    result = _extract("Software that diagnoses a condition; a wrong result could require surgical intervention.")
    assert result.device.software_decision_impact.value == "serious_deterioration_or_surgical_intervention"
    assert result.clarifying_questions == []


def test_software_monitoring_with_vital_danger_context():
    result = _extract("Software that continuously monitors physiological processes in the intensive care unit.")
    assert result.device.software_monitors_physiological_processes is True
    assert result.device.software_monitors_vital_parameters_with_immediate_danger_potential is True
    assert result.clarifying_questions == []


def test_software_monitoring_without_danger_context_asks_question():
    result = _extract("Software that monitors a patient's physiological processes.")
    assert result.device.software_monitors_physiological_processes is True
    assert result.device.software_monitors_vital_parameters_with_immediate_danger_potential is False
    assert len(result.clarifying_questions) == 1
    assert "clinical context" in result.clarifying_questions[0]


# --- Class I sub-qualifiers ---


def test_sterile_qualifier():
    result = _extract("A sterile single-use dressing.")
    assert result.device.placed_on_market_sterile is True


def test_measuring_function_qualifier():
    result = _extract("A digital thermometer that measures body temperature.")
    assert result.device.has_measuring_function is True


def test_reusable_surgical_instrument_qualifier():
    result = _extract("A reusable surgical instrument used for cutting tissue.")
    assert result.device.is_reusable_surgical_instrument is True


# --- Critical anatomy contact ---


def test_contacts_heart():
    result = _extract("A catheter used in direct contact with the heart.")
    assert result.device.contacts_heart_or_central_circulatory_system is True


def test_contacts_central_nervous_system():
    result = _extract("An electrode implanted in direct contact with the brain.")
    assert result.device.contacts_central_nervous_system is True


def test_placed_in_teeth_matches_genuine_tooth_restorations():
    result = _extract("A composite dental filling material placed within the tooth.")
    assert result.device.placed_in_teeth is True


def test_placed_in_teeth_does_not_match_jawbone_anchored_implant():
    """Regression test for the MDCG 2021-24 Note 4 nuance (see
    docs/CLARIFICATIONS_RULE_8.md): a jawbone-anchored dental implant
    post should NOT set placed_in_teeth, since that field means "placed
    within tooth structure," not "implanted near teeth."."""
    result = _extract("A titanium dental implant post anchored in the jawbone.")
    assert result.device.placed_in_teeth is False


# --- Implant categories ---


def test_joint_replacement():
    result = _extract("A total hip replacement prosthesis.")
    assert result.device.is_joint_replacement is True


def test_spinal_column_contact():
    result = _extract("A pedicle screw used in spinal fixation surgery.")
    assert result.device.is_spinal_disc_replacement_or_contacts_spinal_column is True


def test_breast_implant_or_mesh():
    result = _extract("A silicone breast implant.")
    assert result.device.is_breast_implant_or_surgical_mesh is True


def test_active_implantable_device():
    result = _extract("A cardiac pacemaker implanted to regulate heart rhythm.")
    assert result.device.is_active_implantable_or_accessory is True


# --- Physical effects / medicinal content ---


def test_biological_effect_or_absorbed():
    result = _extract("An absorbable suture that is fully resorbed by the body.")
    assert result.device.has_biological_effect_or_wholly_mainly_absorbed is True


def test_administers_medicinal_product():
    result = _extract("A drug-eluting coronary stent.")
    assert result.device.administers_medicinal_product is True


def test_ancillary_medicinal_substance():
    result = _extract("A condom coated with spermicide.")
    assert result.device.contains_ancillary_medicinal_substance is True


def test_contraceptive():
    result = _extract("An intrauterine device (IUD) used for contraception.")
    assert result.device.is_contraceptive_or_sti_prevention is True


def test_xray_recording_device():
    result = _extract("A digital X-ray image detector used in radiography.")
    assert result.device.is_xray_diagnostic_image_recording_device is True


def test_nanomaterial():
    result = _extract("A coating incorporating nanoparticles for antimicrobial effect.")
    assert result.device.contains_nanomaterial is True


def test_inhalation_route():
    result = _extract("A metered-dose inhaler for asthma treatment.")
    assert result.device.administers_medicinal_product_by_inhalation is True


# --- Tissue origin ---


def test_tissue_origin_animal():
    result = _extract("A porcine-derived heart valve.")
    assert result.device.contains_human_or_animal_tissue_or_cells is True
    assert result.device.tissue_origin == TissueOrigin.ANIMAL


def test_tissue_origin_human():
    result = _extract("An allograft bone substitute for spinal fusion.")
    assert result.device.contains_human_or_animal_tissue_or_cells is True
    assert result.device.tissue_origin == TissueOrigin.HUMAN


# --- Wound contact and purpose precedence ---


def test_wound_contact_breached_dermis_priority():
    """Per docs/CLARIFICATIONS_RULE_4.md, when a description could match
    more than one wound-contact purpose, the highest-class purpose should
    be picked - the extractor checks breached-dermis signals before
    micro-environment or barrier signals."""
    result = _extract(
        "A dressing for severe burns that have breached the dermis, "
        "which also helps manage the wound micro-environment."
    )
    assert result.device.contacts_injured_skin_or_mucous_membrane is True
    assert result.device.wound_contact_purpose == WoundContactPurpose.BREACHED_DERMIS_SECONDARY_INTENT_HEALING


def test_wound_contact_microenvironment():
    result = _extract("A hydrogel dressing intended to manage the micro-environment of a wound.")
    assert result.device.wound_contact_purpose == WoundContactPurpose.MANAGE_MICROENVIRONMENT


def test_wound_contact_mechanical_barrier():
    result = _extract("A gauze dressing that absorbs exudate from a minor wound.")
    assert result.device.wound_contact_purpose == WoundContactPurpose.MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION


def test_wound_contact_other_catch_all_with_note():
    result = _extract("A dressing applied to a wound.")
    assert result.device.wound_contact_purpose == WoundContactPurpose.OTHER
    assert any("wound_contact_purpose" in note for note in result.unmatched_notes)


# --- Known, documented (partial) limitation ---


def test_placed_in_teeth_infers_implantable_but_not_invasiveness():
    """This started as a bigger gap: "dental filling" set placed_in_teeth
    but nothing else, so Rule 8's gate (is_implantable OR long-term
    surgically invasive) never fired and the result silently fell through
    to Rule 1's non-invasive default instead of Rule 8's "placed in the
    teeth" exception - see tests/test_extraction_known_devices.py::test_dental_filling_reaches_class_iia_via_rule_8_not_rule_1
    for the full pipeline test.

    Fixed for is_implantable (genuine intra-tooth placement matches
    Article 2(5)'s implantable-device definition - see
    docs/CLARIFICATIONS_RULE_8.md), which is enough to make Rule 8 fire
    correctly. What remains a smaller, honestly-flagged gap: invasiveness
    itself still is not inferred for this phrasing, since "filling" is
    not in the surgical-invasiveness keyword list. Locked in here as the
    residual limitation, not a regression to silently accept."""
    result = _extract("A composite dental filling material placed within the tooth to restore a cavity.")
    assert result.device.placed_in_teeth is True
    assert result.device.is_implantable is True  # fixed: inferred alongside placed_in_teeth
    assert result.device.invasiveness == Invasiveness.NON_INVASIVE  # residual gap: still not inferred
    assert any("invasiveness" in note for note in result.unmatched_notes)
