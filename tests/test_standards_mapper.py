"""Unit tests for each GSPR requirement check (Phase 3) in isolation,
plus end-to-end tests running the full classify -> map pipeline.

Mirrors tests/test_rules_individual.py's structure: each check is tested
directly (not just through the mapper) so a failure points at exactly
which requirement's gating logic is wrong.
"""

from __future__ import annotations

from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from rules_engine.models import (
    ActiveDeviceType,
    ClassificationResult,
    DeviceAttributes,
    DeviceClass,
    Invasiveness,
    SoftwareDecisionImpact,
    TissueOrigin,
)
from standards_mapper.eu_mdr.mapper import EUMDRStandardsMapper
from standards_mapper.eu_mdr.requirements import (
    ALL_REQUIREMENTS,
    ActiveImplantableDevices,
    Biocompatibility,
    BiologicalOriginMaterials,
    ClinicalEvaluation,
    ElectricalMechanicalSafetyAndEMC,
    EnergyOrSubstanceDeliveryDevices,
    IncorporatedMedicinalSubstances,
    InfectionAndSterility,
    LabelingAndInstructionsForUse,
    MeasuringFunction,
    QualityManagementSystem,
    RadiationProtection,
    RiskManagement,
    SoftwareLifecycle,
)


def _result(device_class: DeviceClass | None = None) -> ClassificationResult:
    """Minimal ClassificationResult for unit-testing a single requirement
    check in isolation, without running the full classification engine."""
    return ClassificationResult(device_class=device_class)


# --- Universal requirements (always applies=True) ---


def test_risk_management_always_applies():
    outcome = RiskManagement().evaluate(DeviceAttributes(), _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "ISO 14971"


def test_quality_management_system_always_applies():
    outcome = QualityManagementSystem().evaluate(DeviceAttributes(), _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "ISO 13485"


def test_clinical_evaluation_always_applies():
    outcome = ClinicalEvaluation().evaluate(DeviceAttributes(), _result())
    assert outcome.applies
    assert any(s.standard_id == "ISO 14155" for s in outcome.standards)


def test_clinical_evaluation_notes_investigation_route_for_implantable_class_iii():
    device = DeviceAttributes(is_implantable=True)
    outcome = ClinicalEvaluation().evaluate(device, _result(DeviceClass.III))
    assert "expert panel" in outcome.rationale


def test_labeling_always_applies():
    outcome = LabelingAndInstructionsForUse().evaluate(DeviceAttributes(), _result())
    assert outcome.applies
    ids = {s.standard_id for s in outcome.standards}
    assert ids == {"ISO 15223-1", "ISO 20417"}


def test_labeling_notes_ifu_exception_for_class_i():
    outcome = LabelingAndInstructionsForUse().evaluate(DeviceAttributes(), _result(DeviceClass.I))
    assert "23.1(d)" in outcome.rationale


def test_labeling_no_ifu_exception_note_for_class_iii():
    outcome = LabelingAndInstructionsForUse().evaluate(DeviceAttributes(), _result(DeviceClass.III))
    assert "23.1(d)" not in outcome.rationale


# --- Biocompatibility ---


def test_biocompatibility_applies_when_invasive():
    device = DeviceAttributes(invasiveness=Invasiveness.SURGICALLY_INVASIVE)
    outcome = Biocompatibility().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "ISO 10993-1"


def test_biocompatibility_applies_when_implantable_even_if_not_flagged_invasive():
    device = DeviceAttributes(is_implantable=True)
    outcome = Biocompatibility().evaluate(device, _result())
    assert outcome.applies


def test_biocompatibility_does_not_apply_to_plain_non_invasive_device():
    device = DeviceAttributes(invasiveness=Invasiveness.NON_INVASIVE)
    outcome = Biocompatibility().evaluate(device, _result())
    assert not outcome.applies
    assert outcome.standards == []


def test_biocompatibility_notes_nanomaterial_guidance_when_present():
    device = DeviceAttributes(invasiveness=Invasiveness.SURGICALLY_INVASIVE, contains_nanomaterial=True)
    outcome = Biocompatibility().evaluate(device, _result())
    assert "10993-22" in outcome.limitation_note


# --- Infection and sterility ---


def test_infection_and_sterility_applies_when_sterile():
    device = DeviceAttributes(placed_on_market_sterile=True)
    outcome = InfectionAndSterility().evaluate(device, _result())
    assert outcome.applies
    ids = {s.standard_id for s in outcome.standards}
    assert {"ISO 11135", "ISO 11137", "ISO 17665", "ISO 11607"} == ids


def test_infection_and_sterility_does_not_apply_when_not_sterile():
    outcome = InfectionAndSterility().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Biological origin materials ---


def test_biological_origin_materials_animal_names_iso_22442():
    device = DeviceAttributes(contains_human_or_animal_tissue_or_cells=True, tissue_origin=TissueOrigin.ANIMAL)
    outcome = BiologicalOriginMaterials().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "ISO 22442"


def test_biological_origin_materials_human_names_directive_not_iso_standard():
    device = DeviceAttributes(contains_human_or_animal_tissue_or_cells=True, tissue_origin=TissueOrigin.HUMAN)
    outcome = BiologicalOriginMaterials().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "Directive 2004/23/EC"


def test_biological_origin_materials_does_not_apply_when_absent():
    outcome = BiologicalOriginMaterials().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Incorporated medicinal substances ---


def test_incorporated_medicinal_substances_applies_when_ancillary_substance_present():
    device = DeviceAttributes(contains_ancillary_medicinal_substance=True)
    outcome = IncorporatedMedicinalSubstances().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards == []  # deliberately - not a standards question, see limitation_note
    assert "Directive 2001/83/EC" in outcome.limitation_note


def test_incorporated_medicinal_substances_does_not_apply_when_absent():
    outcome = IncorporatedMedicinalSubstances().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Software lifecycle ---


def test_software_lifecycle_applies_when_software():
    device = DeviceAttributes(is_software=True)
    outcome = SoftwareLifecycle().evaluate(device, _result())
    assert outcome.applies
    ids = {s.standard_id for s in outcome.standards}
    assert {"IEC 62304", "IEC 82304-1", "IEC 81001-5-1"} == ids


def test_software_lifecycle_does_not_apply_to_non_software_device():
    outcome = SoftwareLifecycle().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Electrical/mechanical/EMC ---


def test_electrical_mechanical_emc_applies_when_active():
    device = DeviceAttributes(is_active=True, active_type=ActiveDeviceType.THERAPEUTIC)
    outcome = ElectricalMechanicalSafetyAndEMC().evaluate(device, _result())
    assert outcome.applies
    ids = {s.standard_id for s in outcome.standards}
    assert {"IEC 60601-1", "IEC 60601-1-2"} == ids


def test_electrical_mechanical_emc_does_not_apply_to_passive_device():
    outcome = ElectricalMechanicalSafetyAndEMC().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Radiation protection ---


def test_radiation_protection_applies_when_emits_ionising_radiation():
    device = DeviceAttributes(emits_ionising_radiation_diagnostic_or_interventional=True)
    outcome = RadiationProtection().evaluate(device, _result())
    assert outcome.applies
    assert "2013/59/Euratom" in outcome.rationale


def test_radiation_protection_does_not_apply_without_radiation_signal():
    outcome = RadiationProtection().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Active implantable devices ---


def test_active_implantable_applies_when_both_active_and_implantable():
    device = DeviceAttributes(is_active=True, is_implantable=True)
    outcome = ActiveImplantableDevices().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards[0].standard_id == "ISO 14708-1"


def test_active_implantable_does_not_apply_to_active_only_device():
    device = DeviceAttributes(is_active=True, is_implantable=False)
    outcome = ActiveImplantableDevices().evaluate(device, _result())
    assert not outcome.applies


def test_active_implantable_does_not_apply_to_implantable_only_device():
    device = DeviceAttributes(is_active=False, is_implantable=True)
    outcome = ActiveImplantableDevices().evaluate(device, _result())
    assert not outcome.applies


# --- Measuring function ---


def test_measuring_function_applies_when_flagged():
    device = DeviceAttributes(has_measuring_function=True)
    outcome = MeasuringFunction().evaluate(device, _result())
    assert outcome.applies
    assert outcome.standards == []
    assert outcome.limitation_note != ""


def test_measuring_function_does_not_apply_when_absent():
    outcome = MeasuringFunction().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Energy or substance delivery ---


def test_energy_or_substance_delivery_applies_when_channels_for_infusion():
    device = DeviceAttributes(channels_or_stores_for_infusion_administration_or_introduction=True)
    outcome = EnergyOrSubstanceDeliveryDevices().evaluate(device, _result())
    assert outcome.applies


def test_energy_or_substance_delivery_does_not_apply_when_absent():
    outcome = EnergyOrSubstanceDeliveryDevices().evaluate(DeviceAttributes(), _result())
    assert not outcome.applies


# --- Structural / full-coverage tests ---


def test_all_requirements_list_has_fourteen_categories():
    assert len(ALL_REQUIREMENTS) == 14


def test_mapper_evaluates_every_requirement_category_regardless_of_applicability():
    mapping = EUMDRStandardsMapper().map(DeviceAttributes(), _result())
    assert len(mapping.all_requirements) == 14
    # A bare-default device is non-invasive, non-active, non-software,
    # non-sterile - only the four universal requirements should apply.
    applicable_ids = {r.requirement_id for r in mapping.applicable_requirements}
    assert applicable_ids == {
        "risk_management",
        "quality_management_system",
        "clinical_evaluation",
        "labeling_and_ifu",
    }


def test_every_requirement_has_a_rationale_and_citation_whether_or_not_it_applies():
    mapping = EUMDRStandardsMapper().map(DeviceAttributes(is_active=True, is_software=True), _result())
    for req in mapping.all_requirements:
        assert req.rationale
        assert req.source_citation


# --- End-to-end: classify -> map, against realistic devices ---


def test_end_to_end_hip_implant_triggers_biocompatibility_and_not_software():
    device = DeviceAttributes(
        name="Hip implant",
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        is_implantable=True,
        is_joint_replacement=True,
    )
    classification = EUMDRClassificationEngine().classify(device)
    mapping = EUMDRStandardsMapper().map(device, classification)
    applicable_ids = {r.requirement_id for r in mapping.applicable_requirements}
    assert "biocompatibility" in applicable_ids
    assert "software_lifecycle" not in applicable_ids
    assert "electrical_mechanical_safety_emc" not in applicable_ids


def test_end_to_end_active_implantable_defibrillator_triggers_aimd_and_electrical_and_software():
    device = DeviceAttributes(
        name="Implantable cardioverter defibrillator",
        is_active=True,
        is_implantable=True,
        is_active_implantable_or_accessory=True,
        is_software=True,
        active_type=ActiveDeviceType.THERAPEUTIC,
    )
    classification = EUMDRClassificationEngine().classify(device)
    mapping = EUMDRStandardsMapper().map(device, classification)
    applicable_ids = {r.requirement_id for r in mapping.applicable_requirements}
    assert {
        "active_implantable_devices",
        "electrical_mechanical_safety_emc",
        "software_lifecycle",
        "biocompatibility",
    }.issubset(applicable_ids)


def test_end_to_end_sterile_syringe_triggers_sterility_not_software():
    device = DeviceAttributes(
        name="Hypodermic syringe",
        invasiveness=Invasiveness.SURGICALLY_INVASIVE,
        placed_on_market_sterile=True,
        administers_medicinal_product=True,
    )
    classification = EUMDRClassificationEngine().classify(device)
    mapping = EUMDRStandardsMapper().map(device, classification)
    applicable_ids = {r.requirement_id for r in mapping.applicable_requirements}
    assert "infection_and_sterility" in applicable_ids
    assert "software_lifecycle" not in applicable_ids


def test_end_to_end_standalone_diagnostic_software_triggers_software_not_biocompatibility():
    device = DeviceAttributes(
        name="Diagnostic support app",
        is_active=True,
        is_software=True,
        active_type=ActiveDeviceType.DIAGNOSTIC_MONITORING,
        software_decision_impact=SoftwareDecisionImpact.SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION,
        software_monitors_physiological_processes=True,
    )
    classification = EUMDRClassificationEngine().classify(device)
    mapping = EUMDRStandardsMapper().map(device, classification)
    applicable_ids = {r.requirement_id for r in mapping.applicable_requirements}
    assert "software_lifecycle" in applicable_ids
    assert "electrical_mechanical_safety_emc" in applicable_ids
    assert "biocompatibility" not in applicable_ids
    assert "infection_and_sterility" not in applicable_ids
