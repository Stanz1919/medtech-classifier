"""Structured data model for device attributes and classification results.

This module defines the *input* shape the rules engine consumes (a
``DeviceAttributes`` object) and the *output* shapes it produces
(``RuleOutcome`` / ``ClassificationResult``). Phase 2's extraction layer
will be responsible for turning free text into a ``DeviceAttributes``
instance; nothing here depends on how that object was built.

Terminology and enum values are taken directly from Regulation (EU)
2017/745 Article 2 (Definitions) and Annex VIII Chapter I (Definitions
specific to classification rules). See docs/legal_sources/ for the
verbatim source text this module was written against.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceClass(str, Enum):
    """The four risk classes defined by Annex VIII. Ordered by rank (risk).

    Source: Article 51(1): "Devices shall be divided into classes I, IIa,
    IIb and III, taking into account the intended purpose of the devices
    and their inherent risks."
    """

    I = "I"
    IIA = "IIa"
    IIB = "IIb"
    III = "III"

    @property
    def rank(self) -> int:
        return _CLASS_RANK[self]


_CLASS_RANK = {
    DeviceClass.I: 0,
    DeviceClass.IIA: 1,
    DeviceClass.IIB: 2,
    DeviceClass.III: 3,
}


def highest(*classes: Optional[DeviceClass]) -> Optional[DeviceClass]:
    """Return the highest-risk class among the given classes (None ignored).

    This is the mechanical implementation of Annex VIII Chapter II, point
    3.5: "If several rules, or if, within the same rule, several
    sub-rules, apply to the same device based on the device's intended
    purpose, the strictest rule and sub-rule resulting in the higher
    classification shall apply."
    """
    present = [c for c in classes if c is not None]
    if not present:
        return None
    return max(present, key=lambda c: c.rank)


class ClassQualifier(str, Enum):
    """Informal Class I sub-qualifiers ("Is", "Im", "Ir").

    These are NOT additional Annex VIII classification outcomes. They are
    industry shorthand for a Class I device that also triggers limited
    notified body involvement under Article 52(7), because it is:
      - placed on the market in sterile condition  -> "Is"
      - has a measuring function                    -> "Im"
      - a reusable surgical instrument               -> "Ir"
    A device can carry more than one qualifier at once (e.g. a sterile
    reusable surgical instrument is "Is, Ir"). See
    docs/legal_sources/article_51_and_52_7_classification_and_subqualifiers.txt.
    """

    STERILE = "Is"
    MEASURING_FUNCTION = "Im"
    REUSABLE_SURGICAL_INSTRUMENT = "Ir"


class Invasiveness(str, Enum):
    """Source: Article 2(6) 'invasive device' and Annex VIII 2.2
    'surgically invasive device'."""

    NON_INVASIVE = "non_invasive"
    INVASIVE_BODY_ORIFICE = "invasive_body_orifice"  # invasive via a natural/artificial orifice, not surgically
    SURGICALLY_INVASIVE = "surgically_invasive"


class Duration(str, Enum):
    """Source: Annex VIII Chapter I, Section 1 (Duration of use)."""

    NOT_APPLICABLE = "not_applicable"
    TRANSIENT = "transient"  # < 60 minutes
    SHORT_TERM = "short_term"  # 60 minutes - 30 days
    LONG_TERM = "long_term"  # > 30 days


class ActiveDeviceType(str, Enum):
    """Source: Annex VIII 2.4 'active therapeutic device', 2.5 'active
    device intended for diagnosis and monitoring', and Rule 13's residual
    'all other active devices'."""

    NOT_ACTIVE = "not_active"
    THERAPEUTIC = "therapeutic"
    DIAGNOSTIC_MONITORING = "diagnostic_monitoring"
    OTHER_ACTIVE = "other_active"


class BodyOrificeSite(str, Enum):
    """The three body-orifice sites singled out by Rule 5's exceptions."""

    NOT_APPLICABLE = "not_applicable"
    ORAL_CAVITY_TO_PHARYNX = "oral_cavity_to_pharynx"
    EAR_CANAL_TO_EARDRUM = "ear_canal_to_eardrum"
    NASAL_CAVITY = "nasal_cavity"
    OTHER_ORIFICE = "other_orifice"


class StorageTarget(str, Enum):
    """Source: Rule 2."""

    NONE = "none"
    BLOOD_OR_OTHER_BODY_LIQUIDS = "blood_or_other_body_liquids"
    ORGANS_CELLS_TISSUES = "organs_cells_tissues"
    BLOOD_BAGS = "blood_bags"
    OTHER = "other"


class ModificationTreatmentType(str, Enum):
    """Source: Rule 3."""

    NONE = "none"
    FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE = "filtration_centrifugation_gas_or_heat_exchange"
    OTHER = "other"


class WoundContactPurpose(str, Enum):
    """Source: Rule 4."""

    NONE = "none"
    MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION = "mechanical_barrier_compression_or_absorption"
    MANAGE_MICROENVIRONMENT = "manage_microenvironment"
    BREACHED_DERMIS_SECONDARY_INTENT_HEALING = "breached_dermis_secondary_intent_healing"
    OTHER = "other"


class DisinfectCleanTarget(str, Enum):
    """Source: Rule 16."""

    NONE = "none"
    CONTACT_LENSES = "contact_lenses"
    INVASIVE_DEVICE_END_POINT = "invasive_device_end_point"  # disinfecting solution/washer-disinfector used as end point of processing an invasive device
    OTHER_MEDICAL_DEVICE = "other_medical_device"
    PHYSICAL_ACTION_ONLY_NON_LENS = "physical_action_only_non_lens"  # carve-out: rule does not apply


class TissueOrigin(str, Enum):
    """Source: Rule 18."""

    NONE = "none"
    HUMAN = "human"
    ANIMAL = "animal"


class NanomaterialExposurePotential(str, Enum):
    """Source: Rule 19."""

    NONE = "none"
    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SoftwareDecisionImpact(str, Enum):
    """Source: Rule 11, first paragraph."""

    NOT_APPLICABLE = "not_applicable"
    DEATH_OR_IRREVERSIBLE_DETERIORATION = "death_or_irreversible_deterioration"
    SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION = "serious_deterioration_or_surgical_intervention"
    OTHER_IMPACT = "other_impact"


@dataclass
class DeviceAttributes:
    """Structured attributes of a device, as consumed by the rules engine.

    Every field is optional/defaulted because Phase 2's extractor will
    rarely populate all of them for a given free-text description; a rule
    that needs a field it wasn't given simply treats it as "not stated"
    (falsy) and does not fire. Field groupings mirror the rule groupings
    in Annex VIII Chapter III (non-invasive, invasive, active, special).
    """

    name: str = ""
    description: str = ""

    # --- Chapter I core definitions (Article 2 / Annex VIII 2.x) ---
    invasiveness: Invasiveness = Invasiveness.NON_INVASIVE
    duration: Duration = Duration.NOT_APPLICABLE
    is_implantable: bool = False  # Article 2(5)
    is_active: bool = False  # Article 2(4)
    active_type: ActiveDeviceType = ActiveDeviceType.NOT_ACTIVE
    is_software: bool = False
    # Annex VIII Chapter II, point 3.3 (a general implementing rule, not
    # one of the 22 numbered rules): "Software, which drives a device or
    # influences the use of a device, shall fall within the same class as
    # the device. If the software is independent of any other device, it
    # shall be classified in its own right." When this is set, Rule 11
    # short-circuits to this class directly instead of evaluating its own
    # decision-support/monitoring criteria - e.g. firmware driving a
    # Class IIb infusion pump must be IIb, regardless of what Rule 11's
    # own criteria would otherwise compute for the firmware in isolation.
    # Leave as None for standalone software (the common case), which Rule
    # 11 classifies in its own right as the regulation directs.
    # See docs/CLARIFICATIONS_RULE_11.md.
    drives_or_influences_device_class: Optional[DeviceClass] = None

    # --- Class I sub-qualifiers (Article 52(7)) ---
    placed_on_market_sterile: bool = False
    has_measuring_function: bool = False
    is_reusable_surgical_instrument: bool = False  # also feeds Rule 6

    # --- Body orifice / contact site detail (Rule 5) ---
    body_orifice_site: BodyOrificeSite = BodyOrificeSite.NOT_APPLICABLE
    liable_to_be_absorbed_by_mucous_membrane: bool = False
    connected_to_active_device_class: Optional[DeviceClass] = None

    # --- Contact with critical anatomy (Rules 6-8) ---
    contacts_heart_or_central_circulatory_system: bool = False
    contacts_central_nervous_system: bool = False
    # NARROWER than "dental implant" colloquially suggests. Per MDCG 2021-24
    # Note 4: implants anchored in the jawbone (e.g. a dental implant post/
    # abutment) stay at Rule 8's IIb base class - they do NOT get the "placed
    # in the teeth" -> IIa exception. Only devices genuinely placed within
    # tooth structure (fillings, crowns, bridges, dental alloys/ceramics/
    # polymers) should set this True. See docs/CLARIFICATIONS_RULE_8.md.
    placed_in_teeth: bool = False
    is_spinal_disc_replacement_or_contacts_spinal_column: bool = False
    is_joint_replacement: bool = False
    is_breast_implant_or_surgical_mesh: bool = False
    is_active_implantable_or_accessory: bool = False
    is_ancillary_component: bool = False  # screws, wedges, plates, instruments carve-out in Rule 8

    # --- Shared invasive-device physical effects (Rules 6-8) ---
    supplies_ionising_radiation: bool = False
    has_biological_effect_or_wholly_mainly_absorbed: bool = False
    undergoes_chemical_change_in_body: bool = False
    administers_medicinal_product: bool = False
    administration_potentially_hazardous: bool = False

    # --- Non-invasive rules (Rules 2-4) ---
    channels_or_stores_for_infusion_administration_or_introduction: bool = False
    storage_target: StorageTarget = StorageTarget.NONE
    modifies_biological_or_chemical_composition: bool = False
    modification_treatment_type: ModificationTreatmentType = ModificationTreatmentType.NONE
    in_vitro_direct_contact_with_cells_tissues_organs_or_embryos: bool = False
    contacts_injured_skin_or_mucous_membrane: bool = False
    wound_contact_purpose: WoundContactPurpose = WoundContactPurpose.NONE

    # --- Active device rules (Rules 9-13) ---
    administers_or_exchanges_energy: bool = False
    energy_exchange_potentially_hazardous: bool = False
    controls_monitors_or_influences_therapeutic_class_iib_device: bool = False
    emits_ionising_radiation_therapeutic: bool = False
    emits_ionising_radiation_diagnostic_or_interventional: bool = False
    controls_monitors_or_influences_active_implantable_device: bool = False
    diagnostic_supplies_energy_absorbed_by_body: bool = False
    diagnostic_illuminates_patient_visible_spectrum_only: bool = False
    diagnostic_images_in_vivo_radiopharmaceutical_distribution: bool = False
    diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes: bool = False
    diagnostic_variation_could_cause_immediate_danger: bool = False
    software_decision_impact: SoftwareDecisionImpact = SoftwareDecisionImpact.NOT_APPLICABLE
    software_monitors_physiological_processes: bool = False
    software_monitors_vital_parameters_with_immediate_danger_potential: bool = False
    administers_or_removes_substances_to_from_body: bool = False
    administration_or_removal_potentially_hazardous: bool = False

    # --- Special rules (Rules 14-22) ---
    contains_ancillary_medicinal_substance: bool = False  # Rule 14
    is_contraceptive_or_sti_prevention: bool = False  # Rule 15
    disinfect_clean_target: DisinfectCleanTarget = DisinfectCleanTarget.NONE  # Rule 16
    is_xray_diagnostic_image_recording_device: bool = False  # Rule 17
    contains_human_or_animal_tissue_or_cells: bool = False  # Rule 18
    tissue_origin: TissueOrigin = TissueOrigin.NONE
    tissue_contacts_intact_skin_only: bool = False
    contains_nanomaterial: bool = False  # Rule 19
    nanomaterial_internal_exposure_potential: NanomaterialExposurePotential = NanomaterialExposurePotential.NONE
    administers_medicinal_product_by_inhalation: bool = False  # Rule 20
    inhalation_essential_impact_or_life_threatening: bool = False
    composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin: bool = False  # Rule 21
    systemically_absorbed: bool = False
    achieves_purpose_in_stomach_or_lower_gi_tract: bool = False
    applied_to_skin_or_nasal_oral_cavity_to_pharynx: bool = False
    is_active_therapeutic_with_integrated_diagnostic_function: bool = False  # Rule 22


@dataclass
class RuleOutcome:
    """The result of evaluating a single Annex VIII rule against a device."""

    rule_id: str
    applies: bool
    device_class: Optional[DeviceClass]
    rationale: str
    source_citation: str
    ambiguous: bool = False
    ambiguous_note: Optional[str] = None


@dataclass
class ClassificationResult:
    """The final output of a classification engine's ``classify()`` call."""

    device_class: Optional[DeviceClass]
    qualifiers: list[ClassQualifier] = field(default_factory=list)
    triggered_rules: list[RuleOutcome] = field(default_factory=list)
    all_rule_outcomes: list[RuleOutcome] = field(default_factory=list)
    explanation: str = ""

    @property
    def has_ambiguous_flags(self) -> bool:
        return any(r.ambiguous for r in self.all_rule_outcomes)

    @property
    def ambiguous_outcomes(self) -> list[RuleOutcome]:
        return [r for r in self.all_rule_outcomes if r.ambiguous]
