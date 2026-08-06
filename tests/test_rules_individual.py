"""Unit tests for each Annex VIII rule (1-22) in isolation.

Each rule is tested directly (not through the engine) so a failure
points at exactly which rule's logic is wrong. Where a rule has multiple
"unless" branches, at least the base case and one escalating exception
are covered.
"""

from __future__ import annotations

from rules_engine.eu_mdr.rules import (
    Rule1,
    Rule2,
    Rule3,
    Rule4,
    Rule5,
    Rule6,
    Rule7,
    Rule8,
    Rule9,
    Rule10,
    Rule11,
    Rule12,
    Rule13,
    Rule14,
    Rule15,
    Rule16,
    Rule17,
    Rule18,
    Rule19,
    Rule20,
    Rule21,
    Rule22,
)
from rules_engine.models import (
    ActiveDeviceType,
    BodyOrificeSite,
    DeviceAttributes,
    DeviceClass,
    DisinfectCleanTarget,
    Duration,
    Invasiveness,
    ModificationTreatmentType,
    NanomaterialExposurePotential,
    SoftwareDecisionImpact,
    StorageTarget,
    TissueOrigin,
    WoundContactPurpose,
)


# --- Rule 1 ---


def test_rule1_non_invasive_is_class_i():
    device = DeviceAttributes(invasiveness=Invasiveness.NON_INVASIVE)
    outcome = Rule1().evaluate(device)
    assert outcome.applies
    assert outcome.device_class == DeviceClass.I


def test_rule1_does_not_apply_to_invasive_devices():
    device = DeviceAttributes(invasiveness=Invasiveness.SURGICALLY_INVASIVE)
    outcome = Rule1().evaluate(device)
    assert not outcome.applies
    assert outcome.device_class is None


# --- Rule 2 ---


def test_rule2_blood_storage_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        channels_or_stores_for_infusion_administration_or_introduction=True,
        storage_target=StorageTarget.BLOOD_OR_OTHER_BODY_LIQUIDS,
    )
    outcome = Rule2().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule2_blood_bags_are_class_iib():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        channels_or_stores_for_infusion_administration_or_introduction=True,
        storage_target=StorageTarget.BLOOD_BAGS,
    )
    outcome = Rule2().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule2_other_storage_catch_all_is_class_i():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        channels_or_stores_for_infusion_administration_or_introduction=True,
        storage_target=StorageTarget.OTHER,
    )
    outcome = Rule2().evaluate(device)
    assert outcome.device_class == DeviceClass.I


# --- Rule 3 ---


def test_rule3_modifies_composition_default_is_class_iib():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        modifies_biological_or_chemical_composition=True,
        modification_treatment_type=ModificationTreatmentType.OTHER,
    )
    outcome = Rule3().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule3_filtration_treatment_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        modifies_biological_or_chemical_composition=True,
        modification_treatment_type=ModificationTreatmentType.FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE,
    )
    outcome = Rule3().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule3_in_vitro_embryo_contact_is_class_iii():
    device = DeviceAttributes(
        invasiveness=Invasiveness.NON_INVASIVE,
        in_vitro_direct_contact_with_cells_tissues_organs_or_embryos=True,
    )
    outcome = Rule3().evaluate(device)
    assert outcome.device_class == DeviceClass.III


# --- Rule 4 ---


def test_rule4_mechanical_barrier_is_class_i():
    device = DeviceAttributes(
        contacts_injured_skin_or_mucous_membrane=True,
        wound_contact_purpose=WoundContactPurpose.MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION,
    )
    outcome = Rule4().evaluate(device)
    assert outcome.device_class == DeviceClass.I


def test_rule4_breached_dermis_is_class_iib():
    device = DeviceAttributes(
        contacts_injured_skin_or_mucous_membrane=True,
        wound_contact_purpose=WoundContactPurpose.BREACHED_DERMIS_SECONDARY_INTENT_HEALING,
    )
    outcome = Rule4().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB
    # Not flagged ambiguous: MDCG 2021-24 confirms "highest class wins" is
    # the correct, non-discretionary precedence for Rule 4's bullets - see
    # docs/CLARIFICATIONS_RULE_4.md.
    assert not outcome.ambiguous


def test_rule4_applies_to_invasive_devices_touching_injured_mucous_membrane():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        contacts_injured_skin_or_mucous_membrane=True,
        wound_contact_purpose=WoundContactPurpose.MANAGE_MICROENVIRONMENT,
    )
    outcome = Rule4().evaluate(device)
    assert outcome.applies
    assert outcome.device_class == DeviceClass.IIA


# --- Rule 5 ---


def test_rule5_transient_body_orifice_is_class_i():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.TRANSIENT,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.I


def test_rule5_short_term_non_exempt_orifice_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.SHORT_TERM,
        body_orifice_site=BodyOrificeSite.OTHER_ORIFICE,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule5_short_term_nasal_cavity_exempt_is_class_i():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.SHORT_TERM,
        body_orifice_site=BodyOrificeSite.NASAL_CAVITY,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.I


def test_rule5_long_term_non_exempt_is_class_iib():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.LONG_TERM,
        body_orifice_site=BodyOrificeSite.OTHER_ORIFICE,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule5_long_term_ear_canal_non_absorbed_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.LONG_TERM,
        body_orifice_site=BodyOrificeSite.EAR_CANAL_TO_EARDRUM,
        liable_to_be_absorbed_by_mucous_membrane=False,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule5_connected_to_class_iib_active_device_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        duration=Duration.NOT_APPLICABLE,
        connected_to_active_device_class=DeviceClass.IIB,
    )
    outcome = Rule5().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


# --- Rule 6 ---


def test_rule6_base_transient_surgically_invasive_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.TRANSIENT,
    )
    outcome = Rule6().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule6_heart_contact_is_class_iii():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.TRANSIENT,
        contacts_heart_or_central_circulatory_system=True,
    )
    outcome = Rule6().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule6_reusable_surgical_instrument_is_class_i():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.TRANSIENT,
        is_reusable_surgical_instrument=True,
    )
    outcome = Rule6().evaluate(device)
    assert outcome.device_class == DeviceClass.I


def test_rule6_reusable_instrument_that_also_contacts_heart_is_still_class_iii():
    """Regression test for Annex VIII 3.5: highest classification wins even
    when a de-escalating bullet (reusable instrument -> I) also matches."""
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.TRANSIENT,
        is_reusable_surgical_instrument=True,
        contacts_heart_or_central_circulatory_system=True,
    )
    outcome = Rule6().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule6_does_not_apply_to_implantable_devices():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.TRANSIENT,
        is_implantable=True,
    )
    outcome = Rule6().evaluate(device)
    assert not outcome.applies


# --- Rule 7 ---


def test_rule7_base_short_term_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.SHORT_TERM,
    )
    outcome = Rule7().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule7_biological_effect_is_class_iii():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.SHORT_TERM,
        has_biological_effect_or_wholly_mainly_absorbed=True,
    )
    outcome = Rule7().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule7_chemical_change_placed_in_teeth_is_exempt_to_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.SHORT_TERM,
        undergoes_chemical_change_in_body=True,
        placed_in_teeth=True,
    )
    outcome = Rule7().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


# --- Rule 8 ---


def test_rule8_base_implantable_is_class_iib():
    device = DeviceAttributes(is_implantable=True)
    outcome = Rule8().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule8_placed_in_teeth_is_class_iia():
    device = DeviceAttributes(is_implantable=True, placed_in_teeth=True)
    outcome = Rule8().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule8_breast_implant_is_class_iii():
    device = DeviceAttributes(is_implantable=True, is_breast_implant_or_surgical_mesh=True)
    outcome = Rule8().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule8_joint_replacement_ancillary_screw_is_exempt_from_class_iii():
    device = DeviceAttributes(
        is_implantable=True,
        is_joint_replacement=True,
        is_ancillary_component=True,
    )
    outcome = Rule8().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB  # falls back to Rule 8's base
    assert outcome.ambiguous


def test_rule8_long_term_surgically_invasive_non_implantable_also_covered():
    device = DeviceAttributes(
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        duration=Duration.LONG_TERM,
        is_implantable=False,
    )
    outcome = Rule8().evaluate(device)
    assert outcome.applies
    assert outcome.device_class == DeviceClass.IIB


# --- Rule 9 ---


def test_rule9_therapeutic_energy_exchange_is_class_iia():
    device = DeviceAttributes(
        is_active=True,
        active_type=ActiveDeviceType.THERAPEUTIC,
        administers_or_exchanges_energy=True,
    )
    outcome = Rule9().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule9_hazardous_energy_exchange_is_class_iib():
    device = DeviceAttributes(
        is_active=True,
        active_type=ActiveDeviceType.THERAPEUTIC,
        administers_or_exchanges_energy=True,
        energy_exchange_potentially_hazardous=True,
    )
    outcome = Rule9().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule9_controls_active_implantable_is_class_iii():
    device = DeviceAttributes(
        is_active=True,
        controls_monitors_or_influences_active_implantable_device=True,
    )
    outcome = Rule9().evaluate(device)
    assert outcome.device_class == DeviceClass.III


# --- Rule 10 ---


def test_rule10_direct_diagnosis_default_is_class_iia():
    device = DeviceAttributes(
        is_active=True,
        active_type=ActiveDeviceType.DIAGNOSTIC_MONITORING,
        diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes=True,
    )
    outcome = Rule10().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule10_vital_parameters_immediate_danger_is_class_iib():
    device = DeviceAttributes(
        is_active=True,
        active_type=ActiveDeviceType.DIAGNOSTIC_MONITORING,
        diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes=True,
        diagnostic_variation_could_cause_immediate_danger=True,
    )
    outcome = Rule10().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule10_visible_spectrum_illumination_is_class_i():
    device = DeviceAttributes(
        is_active=True,
        active_type=ActiveDeviceType.DIAGNOSTIC_MONITORING,
        diagnostic_supplies_energy_absorbed_by_body=True,
        diagnostic_illuminates_patient_visible_spectrum_only=True,
    )
    outcome = Rule10().evaluate(device)
    assert outcome.device_class == DeviceClass.I


# --- Rule 11 ---


def test_rule11_other_software_is_class_i():
    device = DeviceAttributes(is_software=True)
    outcome = Rule11().evaluate(device)
    assert outcome.device_class == DeviceClass.I


def test_rule11_decision_support_death_risk_is_class_iii():
    device = DeviceAttributes(
        is_software=True,
        software_decision_impact=SoftwareDecisionImpact.DEATH_OR_IRREVERSIBLE_DETERIORATION,
    )
    outcome = Rule11().evaluate(device)
    assert outcome.device_class == DeviceClass.III
    assert outcome.ambiguous


def test_rule11_monitoring_with_immediate_danger_is_class_iib():
    device = DeviceAttributes(
        is_software=True,
        software_monitors_physiological_processes=True,
        software_monitors_vital_parameters_with_immediate_danger_potential=True,
    )
    outcome = Rule11().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule11_software_driving_a_device_inherits_its_class():
    """Annex VIII Chapter II, point 3.3: software that drives or
    influences another device inherits that device's class outright.
    Firmware driving a Class IIb infusion pump must be IIb, even though
    its own decision-support attributes (OTHER_IMPACT) would otherwise
    compute IIa under Rule 11's standalone criteria - 3.3 short-circuits
    that evaluation entirely. See docs/CLARIFICATIONS_RULE_11.md."""
    device = DeviceAttributes(
        is_software=True,
        software_decision_impact=SoftwareDecisionImpact.OTHER_IMPACT,  # would be IIa alone
        drives_or_influences_device_class=DeviceClass.IIB,
    )
    outcome = Rule11().evaluate(device)
    assert outcome.applies
    assert outcome.device_class == DeviceClass.IIB
    assert not outcome.ambiguous  # 3.3's inheritance is mechanical, not a judgement call
    assert "3.3" in outcome.rationale


def test_rule11_standalone_software_unaffected_by_3_3_field_default():
    """Regression check: leaving drives_or_influences_device_class unset
    (the default / common case) preserves Rule 11's normal standalone
    behaviour."""
    device = DeviceAttributes(is_software=True)
    outcome = Rule11().evaluate(device)
    assert outcome.device_class == DeviceClass.I


# --- Rule 12 ---


def test_rule12_base_administration_is_class_iia():
    device = DeviceAttributes(is_active=True, administers_or_removes_substances_to_from_body=True)
    outcome = Rule12().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule12_hazardous_administration_is_class_iib():
    device = DeviceAttributes(
        is_active=True,
        administers_or_removes_substances_to_from_body=True,
        administration_or_removal_potentially_hazardous=True,
    )
    outcome = Rule12().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


# --- Rule 13 ---


def test_rule13_other_active_device_is_class_i():
    device = DeviceAttributes(is_active=True, active_type=ActiveDeviceType.OTHER_ACTIVE)
    outcome = Rule13().evaluate(device)
    assert outcome.device_class == DeviceClass.I


# --- Rule 14 ---


def test_rule14_ancillary_medicinal_substance_is_class_iii():
    device = DeviceAttributes(contains_ancillary_medicinal_substance=True)
    outcome = Rule14().evaluate(device)
    assert outcome.device_class == DeviceClass.III


# --- Rule 15 ---


def test_rule15_non_implantable_contraceptive_is_class_iib():
    device = DeviceAttributes(is_contraceptive_or_sti_prevention=True)
    outcome = Rule15().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule15_implantable_contraceptive_is_class_iii():
    device = DeviceAttributes(is_contraceptive_or_sti_prevention=True, is_implantable=True)
    outcome = Rule15().evaluate(device)
    assert outcome.device_class == DeviceClass.III


# --- Rule 16 ---


def test_rule16_contact_lens_care_is_class_iib():
    device = DeviceAttributes(disinfect_clean_target=DisinfectCleanTarget.CONTACT_LENSES)
    outcome = Rule16().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


def test_rule16_general_device_disinfection_is_class_iia():
    device = DeviceAttributes(disinfect_clean_target=DisinfectCleanTarget.OTHER_MEDICAL_DEVICE)
    outcome = Rule16().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule16_physical_action_only_carve_out_does_not_apply():
    device = DeviceAttributes(disinfect_clean_target=DisinfectCleanTarget.PHYSICAL_ACTION_ONLY_NON_LENS)
    outcome = Rule16().evaluate(device)
    assert not outcome.applies


# --- Rule 17 ---


def test_rule17_xray_recording_device_is_class_iia():
    device = DeviceAttributes(is_xray_diagnostic_image_recording_device=True)
    outcome = Rule17().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


# --- Rule 18 ---


def test_rule18_human_tissue_device_is_class_iii():
    device = DeviceAttributes(
        contains_human_or_animal_tissue_or_cells=True,
        tissue_origin=TissueOrigin.HUMAN,
    )
    outcome = Rule18().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule18_animal_tissue_intact_skin_only_carve_out():
    device = DeviceAttributes(
        contains_human_or_animal_tissue_or_cells=True,
        tissue_origin=TissueOrigin.ANIMAL,
        tissue_contacts_intact_skin_only=True,
    )
    outcome = Rule18().evaluate(device)
    # Per MDCG 2021-24 Note 3, this carve-out is Class I "in accordance
    # with Rule 1" - a resolved, cited outcome, not left ambiguous. See
    # docs/CLARIFICATIONS_RULE_18.md.
    assert outcome.applies
    assert outcome.device_class == DeviceClass.I
    assert not outcome.ambiguous


# --- Rule 19 ---


def test_rule19_high_exposure_nanomaterial_is_class_iii():
    device = DeviceAttributes(
        contains_nanomaterial=True,
        nanomaterial_internal_exposure_potential=NanomaterialExposurePotential.HIGH,
    )
    outcome = Rule19().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule19_negligible_exposure_nanomaterial_is_class_iia():
    device = DeviceAttributes(
        contains_nanomaterial=True,
        nanomaterial_internal_exposure_potential=NanomaterialExposurePotential.NEGLIGIBLE,
    )
    outcome = Rule19().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


# --- Rule 20 ---


def test_rule20_base_inhalation_is_class_iia():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        administers_medicinal_product_by_inhalation=True,
    )
    outcome = Rule20().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule20_life_threatening_inhalation_is_class_iib():
    device = DeviceAttributes(
        invasiveness=Invasiveness.INVASIVE_BODY_ORIFICE,
        administers_medicinal_product_by_inhalation=True,
        inhalation_essential_impact_or_life_threatening=True,
    )
    outcome = Rule20().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


# --- Rule 21 ---


def test_rule21_systemically_absorbed_is_class_iii():
    device = DeviceAttributes(
        composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin=True,
        systemically_absorbed=True,
    )
    outcome = Rule21().evaluate(device)
    assert outcome.device_class == DeviceClass.III


def test_rule21_skin_local_action_is_class_iia():
    device = DeviceAttributes(
        composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin=True,
        applied_to_skin_or_nasal_oral_cavity_to_pharynx=True,
        systemically_absorbed=False,
    )
    outcome = Rule21().evaluate(device)
    assert outcome.device_class == DeviceClass.IIA


def test_rule21_catch_all_is_class_iib():
    device = DeviceAttributes(
        composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin=True,
        applied_to_skin_or_nasal_oral_cavity_to_pharynx=False,
        systemically_absorbed=False,
    )
    outcome = Rule21().evaluate(device)
    assert outcome.device_class == DeviceClass.IIB


# --- Rule 22 ---


def test_rule22_closed_loop_system_is_class_iii():
    device = DeviceAttributes(
        is_active=True,
        is_active_therapeutic_with_integrated_diagnostic_function=True,
    )
    outcome = Rule22().evaluate(device)
    assert outcome.device_class == DeviceClass.III
