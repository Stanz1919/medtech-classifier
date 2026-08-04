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
