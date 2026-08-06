"""Ground-truth tests against ~28 known real-world device classifications.

Each case is built as a plain dict (the same shape the CLI harness / a
future extraction layer would produce) and run through
``cli.device_attributes_from_dict`` -> ``EUMDRClassificationEngine`` -
i.e. the exact code path ``cli.py`` uses, per the Phase 1 brief's request
to exercise the CLI harness with hand-built attribute dicts.

Expected classes are widely-published, uncontroversial EU MDR
examples (see e.g. MDCG guidance and manufacturer self-classification
documents for these device types). One case (ECG electrodes) is
deliberately NOT forced to match the commonly-cited "IIa" figure - see
the comment on that test for why.
"""

from __future__ import annotations

import pytest

from cli import device_attributes_from_dict
from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from rules_engine.models import ClassQualifier, DeviceClass

CASES = [
    (
        "Surgical examination gloves",
        {"invasiveness": "non_invasive"},
        DeviceClass.I,
        [],
    ),
    (
        "Hypodermic syringe",
        {
            "invasiveness": "surgically_invasive",
            "duration": "transient",
            "administers_medicinal_product": True,
            "administration_potentially_hazardous": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Total hip replacement implant",
        {"is_implantable": True, "is_joint_replacement": True},
        DeviceClass.III,
        [],
    ),
    (
        "Extended-wear contact lenses",
        {
            "invasiveness": "invasive_body_orifice",
            "duration": "long_term",
            "body_orifice_site": "other_orifice",
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Non-absorbable sutures",
        {
            "invasiveness": "surgically_invasive",
            "duration": "short_term",
            "has_biological_effect_or_wholly_mainly_absorbed": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Absorbable sutures",
        {
            "invasiveness": "surgically_invasive",
            "duration": "short_term",
            "has_biological_effect_or_wholly_mainly_absorbed": True,
        },
        DeviceClass.III,
        [],
    ),
    (
        "Bone cement (chemically curing, implanted)",
        {"is_implantable": True, "undergoes_chemical_change_in_body": True, "placed_in_teeth": False},
        DeviceClass.III,
        [],
    ),
    (
        "Blood bag",
        {
            "invasiveness": "non_invasive",
            "channels_or_stores_for_infusion_administration_or_introduction": True,
            "storage_target": "blood_bags",
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Blood collection tube (non-bag)",
        {
            "invasiveness": "non_invasive",
            "channels_or_stores_for_infusion_administration_or_introduction": True,
            "storage_target": "blood_or_other_body_liquids",
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Simple gauze dressing (mechanical barrier)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "mechanical_barrier_compression_or_absorption",
        },
        DeviceClass.I,
        [],
    ),
    (
        "Hydrocolloid dressing (manages micro-environment)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "manage_microenvironment",
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Deep-wound dressing (secondary intent healing)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "breached_dermis_secondary_intent_healing",
        },
        DeviceClass.IIB,
        [],
    ),
    # --- The following four Rule 4 cases are named examples straight out of
    # MDCG 2021-24 Rev.1, "Guidance on classification of medical devices",
    # pages 32-33 (see docs/legal_sources/mdcg_2021-24_rule_4_wound_dressings.txt) ---
    (
        "Ostomy bag (MDCG 2021-24 Rule 4 worked example, Class I)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "mechanical_barrier_compression_or_absorption",
        },
        DeviceClass.I,
        [],
    ),
    (
        "Dressing for burns having breached the dermis (MDCG 2021-24 Rule 4 worked example, Class IIb)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "breached_dermis_secondary_intent_healing",
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Non-medicated impregnated gauze dressing (MDCG 2021-24 Rule 4 worked example, Class IIa)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "manage_microenvironment",
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Dressing for nose bleeds - invasive device on injured mucous membrane, "
        "purpose is absorption not micro-environment management "
        "(MDCG 2021-24 Rule 4 worked example, Class I)",
        {
            "invasiveness": "invasive_body_orifice",
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "mechanical_barrier_compression_or_absorption",
        },
        DeviceClass.I,
        [],
    ),
    (
        "Condom",
        {"is_contraceptive_or_sti_prevention": True},
        DeviceClass.IIB,
        [],
    ),
    (
        "Implantable contraceptive rod",
        {"is_contraceptive_or_sti_prevention": True, "is_implantable": True},
        DeviceClass.III,
        [],
    ),
    (
        "Cardiac pacemaker",
        {"is_implantable": True, "is_active_implantable_or_accessory": True},
        DeviceClass.III,
        [],
    ),
    (
        "Automated external defibrillator",
        {"is_active": True, "is_active_therapeutic_with_integrated_diagnostic_function": True},
        DeviceClass.III,
        [],
    ),
    (
        "Digital hearing aid",
        {
            "is_active": True,
            "active_type": "therapeutic",
            "administers_or_exchanges_energy": True,
            "energy_exchange_potentially_hazardous": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Diagnosis-support software, wrong output -> serious deterioration/surgery",
        {"is_software": True, "software_decision_impact": "serious_deterioration_or_surgical_intervention"},
        DeviceClass.IIB,
        [],
    ),
    (
        "Diagnosis-support software, wrong output -> death risk",
        {"is_software": True, "software_decision_impact": "death_or_irreversible_deterioration"},
        DeviceClass.III,
        [],
    ),
    (
        "Hospital appointment scheduling software",
        {"is_software": True},
        DeviceClass.I,
        [],
    ),
    # --- The following six Rule 11 cases are named examples from MDCG
    # 2021-24 Rev.1, pages 46-47 (see
    # docs/legal_sources/mdcg_2021-24_rule_11_software.txt) ---
    (
        "MDSW performing diagnosis by image analysis for acute stroke treatment decisions "
        "(MDCG 2021-24 Rule 11 named example, Class III)",
        {"is_software": True, "software_decision_impact": "death_or_irreversible_deterioration"},
        DeviceClass.III,
        [],
    ),
    (
        "Mobile app analysing heartbeat, detecting abnormalities, informing a physician "
        "(MDCG 2021-24 Rule 11 named example, Class IIb)",
        {"is_software": True, "software_decision_impact": "serious_deterioration_or_surgical_intervention"},
        DeviceClass.IIB,
        [],
    ),
    (
        "MDSW ranking chemotherapy options for a clinician based on patient history "
        "(MDCG 2021-24 Rule 11 named example, Class IIa)",
        {"is_software": True, "software_decision_impact": "other_impact"},
        DeviceClass.IIA,
        [],
    ),
    (
        "MDSW fertility-tracking app using a validated statistical algorithm "
        "(MDCG 2021-24 Rule 11 named example, Class I)",
        {"is_software": True},
        DeviceClass.I,
        [],
    ),
    (
        "MDSW for continuous vital-process surveillance in anaesthesia/ICU/emergency care "
        "(MDCG 2021-24 Rule 11 named example, Class IIb)",
        {
            "is_software": True,
            "software_monitors_physiological_processes": True,
            "software_monitors_vital_parameters_with_immediate_danger_potential": True,
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "MDSW obtaining routine vital-sign readings at home/check-ups "
        "(MDCG 2021-24 Rule 11 named example, Class IIa)",
        {
            "is_software": True,
            "software_monitors_physiological_processes": True,
            "software_monitors_vital_parameters_with_immediate_danger_potential": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Embedded firmware controlling a Class IIb infusion pump - inherits pump's class "
        "(Annex VIII Chapter II, point 3.3, not evaluated under Rule 11's own criteria)",
        {
            "is_software": True,
            "software_decision_impact": "other_impact",  # would be IIa if evaluated standalone
            "drives_or_influences_device_class": "IIb",
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Digital X-ray image recording device",
        {"is_xray_diagnostic_image_recording_device": True},
        DeviceClass.IIA,
        [],
    ),
    (
        "Central venous catheter",
        {
            "invasiveness": "surgically_invasive",
            "duration": "long_term",
            "contacts_heart_or_central_circulatory_system": True,
        },
        DeviceClass.III,
        [],
    ),
    (
        "Ancillary bone screw within a joint-replacement system",
        {"is_implantable": True, "is_joint_replacement": True, "is_ancillary_component": True},
        DeviceClass.IIB,
        [],
    ),
    # --- The following Rule 8 cases are named examples from MDCG 2021-24
    # Rev.1, pages 38-41 (see docs/legal_sources/mdcg_2021-24_rule_8_implants.txt) ---
    (
        "Pedicle screw for spinal fixation (MDCG 2021-24 Rule 8 named example, ancillary -> IIb)",
        {
            "is_implantable": True,
            "is_spinal_disc_replacement_or_contacts_spinal_column": True,
            "is_ancillary_component": True,
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Hook fixing rod to the spinal column (MDCG 2021-24 Rule 8, Note 7, ancillary -> IIb)",
        {
            "is_implantable": True,
            "is_spinal_disc_replacement_or_contacts_spinal_column": True,
            "is_ancillary_component": True,
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Dental implant post/abutment anchored in jawbone (MDCG 2021-24 Rule 8, Note 4 -> IIb, NOT IIa)",
        {"is_implantable": True, "placed_in_teeth": False},
        DeviceClass.IIB,
        [],
    ),
    (
        "Dental filling material and pins (MDCG 2021-24 Rule 8 named example, genuinely 'in the teeth' -> IIa)",
        {"is_implantable": True, "placed_in_teeth": True},
        DeviceClass.IIA,
        [],
    ),
    (
        "Knee replacement (MDCG 2021-24 Rule 8 named example, Class III)",
        {"is_implantable": True, "is_joint_replacement": True, "is_ancillary_component": False},
        DeviceClass.III,
        [],
    ),
    (
        "Interbody spinal fusion device (MDCG 2021-24 Rule 8 named example, Class III)",
        {
            "is_implantable": True,
            "is_spinal_disc_replacement_or_contacts_spinal_column": True,
            "is_ancillary_component": False,
        },
        DeviceClass.III,
        [],
    ),
    (
        "Nasal cannula for oxygen delivery (transient)",
        {
            "invasiveness": "invasive_body_orifice",
            "duration": "transient",
            "body_orifice_site": "nasal_cavity",
        },
        DeviceClass.I,
        [],
    ),
    (
        "High-exposure nanomaterial-coated implant",
        {
            "is_implantable": True,
            "contains_nanomaterial": True,
            "nanomaterial_internal_exposure_potential": "high",
        },
        DeviceClass.III,
        [],
    ),
    # --- The following seven Rule 18 cases are named examples from MDCG
    # 2021-24 Rev.1, pages 53-54 (see
    # docs/legal_sources/mdcg_2021-24_rule_18_tissue_devices.txt) ---
    (
        "Animal-derived biological heart valve (MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "animal"},
        DeviceClass.III,
        [],
    ),
    (
        "Porcine xenograft dressing (MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "animal"},
        DeviceClass.III,
        [],
    ),
    (
        "Collagen dermal filler, animal-sourced (MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "animal"},
        DeviceClass.III,
        [],
    ),
    (
        "Bone graft substitute (MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "human"},
        DeviceClass.III,
        [],
    ),
    (
        "Device made from animal-sourced collagen/gelatine (MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "animal"},
        DeviceClass.III,
        [],
    ),
    (
        "Substance-based device containing collagen for use in body orifices "
        "(MDCG 2021-24 Rule 18 named example, Class III)",
        {"contains_human_or_animal_tissue_or_cells": True, "tissue_origin": "human"},
        DeviceClass.III,
        [],
    ),
    (
        "Leather components of orthopaedic appliances - animal-derived, intact skin contact only "
        "(MDCG 2021-24 Rule 18 named example + Note 3, Class I via Rule 1)",
        {
            "contains_human_or_animal_tissue_or_cells": True,
            "tissue_origin": "animal",
            "tissue_contacts_intact_skin_only": True,
        },
        DeviceClass.I,
        [],
    ),
    (
        "Sterile primary wound dressing (mechanical barrier)",
        {
            "contacts_injured_skin_or_mucous_membrane": True,
            "wound_contact_purpose": "mechanical_barrier_compression_or_absorption",
            "placed_on_market_sterile": True,
        },
        DeviceClass.I,
        [ClassQualifier.STERILE],
    ),
    (
        "Reusable surgical scissors",
        {
            "invasiveness": "surgically_invasive",
            "duration": "transient",
            "is_reusable_surgical_instrument": True,
        },
        DeviceClass.I,
        [ClassQualifier.REUSABLE_SURGICAL_INSTRUMENT],
    ),
    (
        "Non-invasive digital thermometer (measuring function)",
        {"invasiveness": "non_invasive", "has_measuring_function": True},
        DeviceClass.I,
        [ClassQualifier.MEASURING_FUNCTION],
    ),
    (
        "Sterile reusable surgical instrument",
        {
            "invasiveness": "surgically_invasive",
            "duration": "transient",
            "is_reusable_surgical_instrument": True,
            "placed_on_market_sterile": True,
        },
        DeviceClass.I,
        [ClassQualifier.STERILE, ClassQualifier.REUSABLE_SURGICAL_INSTRUMENT],
    ),
    # =========================================================================
    # The following cases fill the "gap rules" identified in PHASE_2_ROADMAP.md
    # (Rules 3, 10, 12, 13, 14, 16, 20, 21 previously had unit-test coverage
    # but no realistic device exercising them end-to-end). All examples below
    # are named verbatim in MDCG 2021-24 Rev.1's worked-examples tables - see
    # the cited page numbers and docs/legal_sources/mdcg_2021-24_rule_*.txt.
    # =========================================================================
    # --- Rule 3 (MDCG 2021-24, pages 30-31) ---
    (
        "Haemodialyser removing blood solutes by exchange (MDCG 2021-24 Rule 3 named example, Class IIb)",
        {
            "invasiveness": "non_invasive",
            "modifies_biological_or_chemical_composition": True,
            "modification_treatment_type": "other",
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Particulate blood filtration in an extracorporeal circulation system "
        "(MDCG 2021-24 Rule 3 named example, Class IIa)",
        {
            "invasiveness": "non_invasive",
            "modifies_biological_or_chemical_composition": True,
            "modification_treatment_type": "filtration_centrifugation_gas_or_heat_exchange",
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "IVF cell media without human albumin (MDCG 2021-24 Rule 3 named example, Class III)",
        {"invasiveness": "non_invasive", "in_vitro_direct_contact_with_cells_tissues_organs_or_embryos": True},
        DeviceClass.III,
        [],
    ),
    # --- Rule 10 (MDCG 2021-24, pages 44-45) ---
    (
        "Diagnostic ultrasound equipment (MDCG 2021-24 Rule 10 named example, Class IIa)",
        {
            "is_active": True,
            "active_type": "diagnostic_monitoring",
            "diagnostic_supplies_energy_absorbed_by_body": True,
            "diagnostic_illuminates_patient_visible_spectrum_only": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Examination lamp - illumination only (MDCG 2021-24 Rule 10 named example, Class I)",
        {
            "is_active": True,
            "active_type": "diagnostic_monitoring",
            "diagnostic_supplies_energy_absorbed_by_body": True,
            "diagnostic_illuminates_patient_visible_spectrum_only": True,
        },
        DeviceClass.I,
        [],
    ),
    (
        "Electrocardiograph for routine use (MDCG 2021-24 Rule 10 named example, Class IIa)",
        {
            "is_active": True,
            "active_type": "diagnostic_monitoring",
            "diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes": True,
            "diagnostic_variation_could_cause_immediate_danger": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "ICU multi-parameter patient monitor (MDCG 2021-24 Rule 10 named example, Class IIb)",
        {
            "is_active": True,
            "active_type": "diagnostic_monitoring",
            "diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes": True,
            "diagnostic_variation_could_cause_immediate_danger": True,
        },
        DeviceClass.IIB,
        [],
    ),
    (
        "Diagnostic CT scanner (MDCG 2021-24 Rule 10 named example, Class IIb)",
        {"is_active": True, "emits_ionising_radiation_diagnostic_or_interventional": True},
        DeviceClass.IIB,
        [],
    ),
    # --- Rule 12 (MDCG 2021-24, page 48) ---
    (
        "Suction pump, routine use (MDCG 2021-24 Rule 12 named example, Class IIa)",
        {
            "is_active": True,
            "administers_or_removes_substances_to_from_body": True,
            "administration_or_removal_potentially_hazardous": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Anaesthesia machine (MDCG 2021-24 Rule 12 named example, Class IIb)",
        {
            "is_active": True,
            "administers_or_removes_substances_to_from_body": True,
            "administration_or_removal_potentially_hazardous": True,
        },
        DeviceClass.IIB,
        [],
    ),
    # --- Rule 13 (MDCG 2021-24, pages 48-49) ---
    (
        "Electric wheelchair (MDCG 2021-24 Rule 13 named example, Class I)",
        {"is_active": True, "active_type": "other_active"},
        DeviceClass.I,
        [],
    ),
    (
        "Dental curing light (MDCG 2021-24 Rule 13 named example, Class I)",
        {"is_active": True, "active_type": "other_active"},
        DeviceClass.I,
        [],
    ),
    # --- Rule 14 (MDCG 2021-24, pages 49-50) ---
    (
        "Bone cement with antibiotics (MDCG 2021-24 Rule 14 named example, Class III)",
        {"contains_ancillary_medicinal_substance": True},
        DeviceClass.III,
        [],
    ),
    (
        "Condom with spermicide - Rule 14 overrides Rule 15's IIb "
        "(MDCG 2021-24 Rule 14 named example, Class III)",
        {"contains_ancillary_medicinal_substance": True, "is_contraceptive_or_sti_prevention": True},
        DeviceClass.III,
        [],
    ),
    (
        "Drug-eluting coronary stent (MDCG 2021-24 Rule 14 named example, Class III)",
        {
            "contains_ancillary_medicinal_substance": True,
            "is_implantable": True,
            "contacts_heart_or_central_circulatory_system": True,
        },
        DeviceClass.III,
        [],
    ),
    # --- Rule 16 (MDCG 2021-24, pages 51-52) ---
    (
        "Contact lens storing solution (MDCG 2021-24 Rule 16 named example, Class IIb)",
        {"disinfect_clean_target": "contact_lenses"},
        DeviceClass.IIB,
        [],
    ),
    (
        "Disinfecting solution for non-invasive medical devices (MDCG 2021-24 Rule 16 named example, Class IIa)",
        {"disinfect_clean_target": "other_medical_device"},
        DeviceClass.IIA,
        [],
    ),
    (
        "Washer-disinfector for endoscopes at end of processing (MDCG 2021-24 Rule 16 named example, Class IIb)",
        {"disinfect_clean_target": "invasive_device_end_point"},
        DeviceClass.IIB,
        [],
    ),
    (
        "Brush for mechanical cleaning of non-lens devices - carve-out, falls to Rule 1 "
        "(MDCG 2021-24 Rule 16 named example, Class I)",
        {"invasiveness": "non_invasive", "disinfect_clean_target": "physical_action_only_non_lens"},
        DeviceClass.I,
        [],
    ),
    # --- Rule 20 (MDCG 2021-24, pages 56-57) ---
    (
        "Inhaler for nicotine replacement therapy (MDCG 2021-24 Rule 20 named example, Class IIa)",
        {
            "invasiveness": "invasive_body_orifice",
            "administers_medicinal_product_by_inhalation": True,
            "inhalation_essential_impact_or_life_threatening": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Nebuliser where dosage-delivery failure could be hazardous "
        "(MDCG 2021-24 Rule 20 named example, Class IIb)",
        {
            "invasiveness": "invasive_body_orifice",
            "administers_medicinal_product_by_inhalation": True,
            "inhalation_essential_impact_or_life_threatening": True,
        },
        DeviceClass.IIB,
        [],
    ),
    # --- Rule 21 (MDCG 2021-24, pages 57-58) ---
    (
        "Fat absorber, systemically absorbed (MDCG 2021-24 Rule 21 named example, Class III)",
        {
            "composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin": True,
            "systemically_absorbed": True,
        },
        DeviceClass.III,
        [],
    ),
    (
        "Saline nasal/throat spray, local action only (MDCG 2021-24 Rule 21 named example, Class IIa)",
        {
            "composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin": True,
            "applied_to_skin_or_nasal_oral_cavity_to_pharynx": True,
            "systemically_absorbed": False,
        },
        DeviceClass.IIA,
        [],
    ),
    (
        "Vaginal moisturising gel/lubricant - catch-all case "
        "(MDCG 2021-24 Rule 21 named example, Class IIb)",
        {
            "composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin": True,
            "applied_to_skin_or_nasal_oral_cavity_to_pharynx": False,
            "systemically_absorbed": False,
        },
        DeviceClass.IIB,
        [],
    ),
]


@pytest.mark.parametrize("name,data,expected_class,expected_qualifiers", CASES, ids=[c[0] for c in CASES])
def test_known_device_classification(name, data, expected_class, expected_qualifiers):
    device = device_attributes_from_dict(data)
    device.name = name
    result = EUMDRClassificationEngine().classify(device)
    assert result.device_class == expected_class, (
        f"{name}: expected Class {expected_class.value}, got "
        f"{result.device_class.value if result.device_class else None}. "
        f"Triggered rules: {[o.rule_id for o in result.triggered_rules]}"
    )
    assert result.qualifiers == expected_qualifiers, f"{name}: qualifier mismatch"


def test_passive_ecg_electrodes_literal_annex_viii_reading_is_class_i():
    """Documented divergence from common industry practice.

    Many published device-classification examples list basic ECG surface
    electrodes as Class IIa. But a bare adhesive Ag/AgCl electrode is not
    an "active device" under Article 2(4) (its operation does not depend
    on an energy source other than the body), so Rule 10 ("active devices
    intended for diagnosis and monitoring") cannot literally apply to it,
    and no other Annex VIII rule (1-9, 11-22) covers a plain non-invasive
    skin-contact conductor either. The strict, literal reading this
    engine implements therefore gives Class I via Rule 1.

    The "IIa" figure commonly cited in industry lists reflects
    manufacturers/notified bodies treating the electrode as inseparable
    from the active diagnostic monitoring system it plugs into - an
    interpretive extension beyond Annex VIII's text, not a mechanical
    application of it. Per the brief's instruction not to force false
    confidence, this test asserts what the rules actually say rather than
    silently matching the commonly-cited figure.
    """
    device = device_attributes_from_dict(
        {
            "name": "ECG surface electrode",
            "invasiveness": "non_invasive",
            "is_active": False,
        }
    )
    result = EUMDRClassificationEngine().classify(device)
    assert result.device_class == DeviceClass.I
