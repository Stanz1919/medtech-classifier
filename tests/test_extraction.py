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
    BodyOrificeSite,
    DisinfectCleanTarget,
    Duration,
    Invasiveness,
    ModificationTreatmentType,
    StorageTarget,
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


# =========================================================================
# Comprehensive grounding pass: Rules 2, 3, 5, 6-10, 12, 16, 18, 20-22
# =========================================================================
# Added when deepening keyword coverage from 30/65 to 56/65 DeviceAttributes
# fields, grounded in the exact Annex VIII/Article 2 text (see
# extraction/keyword_extractor.py's module docstring for the full list).
# Several genuine bugs were found and fixed while writing these tests -
# each is called out explicitly rather than silently folded in.


# --- Central circulatory system / CNS (Annex VIII 2.6, 2.7) ---
# The starting point for this pass: generic words like "heart" or "brain"
# aren't the actual definitions - 2.6 is an exhaustive list of specific
# named vessels, and 2.7 easily loses "meninges" if grounded from common
# sense instead of the definition text itself.


def test_central_circulatory_system_latin_vessel_name():
    result = _extract("A catheter placed in the truncus brachiocephalicus.")
    assert result.device.contacts_heart_or_central_circulatory_system is True


def test_central_circulatory_system_english_vessel_name():
    result = _extract("A stent placed in the superior vena cava.")
    assert result.device.contacts_heart_or_central_circulatory_system is True


def test_central_nervous_system_meninges_not_missed():
    result = _extract("A device intended for direct contact with the meninges.")
    assert result.device.contacts_central_nervous_system is True


# --- Rule 2 ---


def test_rule2_channels_stores_blood():
    result = _extract("A non-invasive device intended for storing blood for eventual infusion into the body.")
    assert result.device.channels_or_stores_for_infusion_administration_or_introduction is True
    assert result.device.storage_target == StorageTarget.BLOOD_OR_OTHER_BODY_LIQUIDS


def test_rule2_storage_target_blood_bags():
    result = _extract("A blood bag for storing blood.")
    assert result.device.storage_target == StorageTarget.BLOOD_BAGS


def test_rule2_storage_target_organs():
    result = _extract("A non-invasive device for storing organs for eventual transplantation.")
    assert result.device.storage_target == StorageTarget.ORGANS_CELLS_TISSUES


def test_rule2_storage_target_catch_all_with_note():
    result = _extract("A non-invasive device for channelling gas for eventual administration into the body.")
    assert result.device.channels_or_stores_for_infusion_administration_or_introduction is True
    assert result.device.storage_target == StorageTarget.OTHER
    assert any("storage_target" in note for note in result.unmatched_notes)


# --- Rule 3 ---


def test_rule3_modifies_composition_with_filtration():
    result = _extract("A non-invasive device that modifies the biological composition of blood by filtration.")
    assert result.device.modifies_biological_or_chemical_composition is True
    assert result.device.modification_treatment_type == ModificationTreatmentType.FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE


def test_rule3_modifies_composition_other_treatment():
    result = _extract("A device that modifies the chemical composition of other body liquids by an unspecified process.")
    assert result.device.modification_treatment_type == ModificationTreatmentType.OTHER


def test_rule3_in_vitro_contact():
    result = _extract("A substance used in vitro in direct contact with human cells taken from the body.")
    assert result.device.in_vitro_direct_contact_with_cells_tissues_organs_or_embryos is True


# --- Rule 5 body-orifice site + absorption ---


def test_rule5_body_orifice_site_oral():
    result = _extract("A device inserted in the oral cavity as far as the pharynx.")
    assert result.device.body_orifice_site == BodyOrificeSite.ORAL_CAVITY_TO_PHARYNX


def test_rule5_body_orifice_site_ear():
    result = _extract("A hearing device inserted into the ear canal.")
    assert result.device.body_orifice_site == BodyOrificeSite.EAR_CANAL_TO_EARDRUM


def test_rule5_body_orifice_site_nasal():
    result = _extract("A device inserted in the nasal cavity.")
    assert result.device.body_orifice_site == BodyOrificeSite.NASAL_CAVITY


def test_rule5_liable_to_be_absorbed():
    result = _extract("A device in the nasal cavity that is liable to be absorbed by the mucous membrane.")
    assert result.device.liable_to_be_absorbed_by_mucous_membrane is True


def test_rule5_not_liable_to_be_absorbed_negation():
    """Regression test: 'not liable to be absorbed' contains 'liable to
    be absorbed' as a substring, so the positive signal must not win."""
    result = _extract("A device in the ear canal that is not liable to be absorbed by the mucous membrane.")
    assert result.device.liable_to_be_absorbed_by_mucous_membrane is False


# --- Rules 6-8 shared physical effects ---


def test_ionising_radiation_british_spelling():
    result = _extract("A surgically invasive device intended to supply ionising radiation.")
    assert result.device.supplies_ionising_radiation is True


def test_ionising_radiation_american_spelling():
    """The regulation itself is inconsistent about spelling this across
    rules (Rule 6: 'ionising'; Rule 7: 'ionizing') - both must match."""
    result = _extract("A surgically invasive device intended to supply ionizing radiation.")
    assert result.device.supplies_ionising_radiation is True


def test_undergoes_chemical_change():
    result = _extract("An implantable device that will undergo chemical change in the body.")
    assert result.device.undergoes_chemical_change_in_body is True


# --- Rule 9 ---


def test_rule9_administers_or_exchanges_energy():
    result = _extract("An active therapeutic device that administers or exchanges energy to treat pain.")
    assert result.device.administers_or_exchanges_energy is True


def test_rule9_emits_ionising_radiation_therapeutic():
    result = _extract("An active device that emits ionising radiation for therapeutic purposes (radiotherapy).")
    assert result.device.emits_ionising_radiation_therapeutic is True


# --- Rule 10 ---


def test_rule10_diagnostic_energy_absorbed():
    result = _extract("An active diagnostic device that supplies energy which will be absorbed by the human body.")
    assert result.device.diagnostic_supplies_energy_absorbed_by_body is True


def test_rule10_illuminate_visible_spectrum():
    result = _extract("An active diagnostic device intended to illuminate the patient's body in the visible spectrum.")
    assert result.device.diagnostic_illuminates_patient_visible_spectrum_only is True


def test_rule10_radiopharmaceutical_imaging():
    result = _extract("An active device intended to image in vivo distribution of radiopharmaceuticals.")
    assert result.device.diagnostic_images_in_vivo_radiopharmaceutical_distribution is True


def test_rule10_direct_diagnosis_vital_with_immediate_danger():
    result = _extract(
        "An active device for direct diagnosis of vital physiological processes; "
        "variations could cause immediate danger, e.g. cardiac performance."
    )
    assert result.device.diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes is True
    assert result.device.diagnostic_variation_could_cause_immediate_danger is True
    assert result.clarifying_questions == []


def test_rule10_direct_diagnosis_vital_without_danger_signal_asks_question():
    result = _extract("An active device for direct diagnosis of vital physiological processes.")
    assert result.device.diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes is True
    assert result.device.diagnostic_variation_could_cause_immediate_danger is False
    assert len(result.clarifying_questions) == 1
    assert "Class IIb" in result.clarifying_questions[0]


def test_rule10_diagnostic_therapeutic_radiology():
    result = _extract("A CT scanner used for diagnostic radiology.")
    assert result.device.emits_ionising_radiation_diagnostic_or_interventional is True


# --- Rule 12 ---


def test_rule12_administers_and_removes_substances():
    """Regression test: the regex must not require the literal word
    'and/or' - real text says 'administers and removes', not
    'administers and/or removes'."""
    result = _extract("An active device that administers and removes body liquids from the patient.")
    assert result.device.administers_or_removes_substances_to_from_body is True


def test_rule12_named_device_type():
    result = _extract("A suction pump.")
    # "suction pump" alone doesn't set is_active via the power-keyword
    # list, but the device-type phrase itself is a Rule 12 signal -
    # confirms is_active gating doesn't block this from being logged even
    # when the pump isn't independently flagged as active by other means.
    assert result.device.administers_or_removes_substances_to_from_body is True


# --- Rule 16 ---


def test_rule16_contact_lens_care():
    result = _extract("A solution intended for disinfecting and hydrating contact lenses.")
    assert result.device.disinfect_clean_target == DisinfectCleanTarget.CONTACT_LENSES


def test_rule16_invasive_device_end_point():
    result = _extract("A washer-disinfector for invasive devices such as endoscopes, used as the end point of processing.")
    assert result.device.disinfect_clean_target == DisinfectCleanTarget.INVASIVE_DEVICE_END_POINT


def test_rule16_other_medical_device():
    result = _extract("A solution intended for disinfecting medical devices.")
    assert result.device.disinfect_clean_target == DisinfectCleanTarget.OTHER_MEDICAL_DEVICE


def test_rule16_physical_action_only_carve_out():
    result = _extract("A brush intended for disinfecting medical devices by physical action only.")
    assert result.device.disinfect_clean_target == DisinfectCleanTarget.PHYSICAL_ACTION_ONLY_NON_LENS


# --- Rule 18 ---


def test_rule18_generic_animal_tissue_phrase():
    """Regression test: the original signal list only had specific
    species (porcine/bovine) and 'animal-derived/origin/sourced' - the
    plain phrase 'animal tissue' itself was missing."""
    result = _extract("A device made from animal tissue.")
    assert result.device.contains_human_or_animal_tissue_or_cells is True
    assert result.device.tissue_origin == TissueOrigin.ANIMAL


def test_rule18_intact_skin_only_carve_out():
    result = _extract("A device made from animal tissue intended for contact with intact skin only.")
    assert result.device.tissue_contacts_intact_skin_only is True


# --- Rule 20 ---


def test_rule20_life_threatening():
    result = _extract("An inhaler intended to treat life-threatening conditions.")
    assert result.device.inhalation_essential_impact_or_life_threatening is True


# --- Rule 21 ---


def test_rule21_systemically_absorbed():
    result = _extract("A substance systemically absorbed by the human body after being introduced via a body orifice.")
    assert result.device.systemically_absorbed is True


def test_rule21_not_systemically_absorbed_negation():
    """Regression test: 'not systemically absorbed' contains
    'systemically absorbed' as a substring, so the positive signal must
    not win - same bug class as Rule 5's liable/not-liable case."""
    result = _extract(
        "A substance composed of substances applied to the skin, achieving its "
        "intended purpose locally, not systemically absorbed."
    )
    assert result.device.systemically_absorbed is False


def test_rule21_stomach_lower_gi():
    result = _extract("A substance composed of substances that achieves its intended purpose in the stomach.")
    assert result.device.achieves_purpose_in_stomach_or_lower_gi_tract is True


def test_rule21_applied_to_skin():
    result = _extract("A substance composed of substances applied to the skin.")
    assert result.device.applied_to_skin_or_nasal_oral_cavity_to_pharynx is True


# --- Rule 22 ---


def test_rule22_closed_loop_system():
    result = _extract("An active therapeutic device that is part of a closed-loop system.")
    assert result.device.is_active_therapeutic_with_integrated_diagnostic_function is True


def test_rule22_automated_external_defibrillator():
    result = _extract("An automated external defibrillator with an integrated diagnostic function.")
    assert result.device.is_active_therapeutic_with_integrated_diagnostic_function is True


# --- is_active detection bugs found and fixed during this pass ---


def test_is_active_from_literal_phrase():
    """Regression test: the literal phrase 'active device' (or 'active
    therapeutic/diagnostic/implantable device') was not recognised at
    all - only indirect power-source vocabulary (battery, electronic,
    etc.) was. A device description using the regulation's own term for
    itself must be recognised."""
    result = _extract("An active device that monitors patient status.")
    assert result.device.is_active is True


def test_is_active_from_therapeutic_function_alone():
    """Regression test: Annex VIII 2.4 defines 'active therapeutic
    device' as ITSELF a subtype of active device - so therapeutic
    function vocabulary (therapy, treat, stimulate...) is sufficient
    evidence for is_active on its own, without also requiring a separate
    battery/powered keyword."""
    result = _extract("A device that delivers therapy to alleviate pain.")
    assert result.device.is_active is True
    assert result.device.active_type == ActiveDeviceType.THERAPEUTIC


def test_is_active_from_diagnostic_function_alone():
    """Same bug class as above, for Annex VIII 2.5: 'a CT scanner' has no
    power-source keyword but is unambiguously an active diagnostic
    device."""
    result = _extract("A CT scanner used for diagnostic radiology.")
    assert result.device.is_active is True
    assert result.device.active_type == ActiveDeviceType.DIAGNOSTIC_MONITORING


def test_automated_external_defibrillator_does_not_falsely_match_implantable_signal():
    """Regression test: the original implantable-defibrillator pattern
    made both 'implantable' and 'cardioverter' optional, so it matched
    bare 'defibrillator' - meaning an explicitly EXTERNAL automated
    defibrillator (AED) falsely set is_active_implantable_or_accessory.
    AEDs are not implantable; they belong under Rule 22 instead."""
    result = _extract("An automated external defibrillator with an integrated diagnostic function.")
    assert result.device.is_active_implantable_or_accessory is False


def test_implantable_cardioverter_defibrillator_still_matches():
    """Confirms the AED fix above didn't overcorrect: a genuine ICD must
    still match."""
    result = _extract("An implantable cardioverter defibrillator (ICD) implanted permanently.")
    assert result.device.is_active_implantable_or_accessory is True
