"""EU MDR 2017/745 General Safety and Performance Requirement (GSPR) checks.

Every class below is written against the verbatim text saved in
docs/legal_sources/annex_i_general_safety_performance_requirements.txt
(Annex I, fetched from EUR-Lex CELEX:32017R0745, retrieved 2026-08-10),
plus two short extracts of provisions Annex I itself refers out to:
docs/legal_sources/article_61_clinical_evaluation_extract.txt and
docs/legal_sources/article_10_9_quality_management_system_extract.txt.
Each class's docstring quotes the operative part of the requirement; the
``source_citation`` attribute points back to the specific point number.

Standard designations are given WITHOUT an edition year on purpose.
Standards are periodically revised (ISO 14971, ISO 13485, IEC 62304 etc.
have all been revised or amended since first publication) and this
module has no live link to check which edition currently applies -
always verify the current edition, and current EU-harmonised status
under Article 8, before relying on a citation here. See
standards_mapper/base.py's module docstring for the fuller "commonly
used, not a compliance determination" framing every ``StandardApplicability``
should be read under.

Coverage: 14 GSPR categories, chosen because each maps to an identifiable
standard or clearly distinct legal obligation. Annex I contains GSPR
points this module does NOT check, documented here rather than silently
skipped:
  - Section 9 (the Annex XVI "no medical purpose" products list, e.g.
    coloured contact lenses) - DeviceAttributes has no field for "is an
    Annex XVI product" and the classifier's scope is Annex VIII devices.
  - Section 10.4 (CMR / endocrine-disrupting substance concentration
    limits and labelling) - no field captures substance-level
    composition; folded into Biocompatibility's limitation note instead
    of a fabricated dedicated check.
  - Section 22 (devices intended for lay/home use) - no field captures
    intended user population (professional vs. lay), so this GSPR
    category is not evaluated at all, rather than guessed at.
"""

from __future__ import annotations

from rules_engine.models import ClassificationResult, DeviceAttributes, DeviceClass, Invasiveness, TissueOrigin
from standards_mapper.base import GSPRRequirement, GSPRRequirementCheck, StandardApplicability

_SOURCE_BASE = "Regulation (EU) 2017/745, Annex I"


def _has_biological_contact(device: DeviceAttributes) -> bool:
    """True if anything about the device suggests it contacts human
    tissue, cells, or body fluids in a way Annex I 10.1(b) and 10.2
    address - not just "invasive" in the Annex VIII classification
    sense, since 10.1(b) speaks generally of "compatibility between the
    materials and substances used and biological tissues, cells and
    body fluids", not only surgically invasive devices."""
    return (
        device.invasiveness != Invasiveness.NON_INVASIVE
        or device.is_implantable
        or device.contacts_injured_skin_or_mucous_membrane
        or device.contacts_heart_or_central_circulatory_system
        or device.contacts_central_nervous_system
        or device.in_vitro_direct_contact_with_cells_tissues_organs_or_embryos
        or device.tissue_contacts_intact_skin_only
        or device.placed_in_teeth
        or device.is_spinal_disc_replacement_or_contacts_spinal_column
        or device.is_joint_replacement
        or device.is_breast_implant_or_surgical_mesh
    )


class RiskManagement(GSPRRequirementCheck):
    """Universal - risk management system.

    "Manufacturers shall establish, implement, document and maintain a
    risk management system. Risk management shall be understood as a
    continuous iterative process throughout the entire lifecycle of a
    device..." (Annex I, Section 3)
    """

    requirement_id = "risk_management"
    title = "Risk management system"
    source_citation = f"{_SOURCE_BASE}, Section 3"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=True,
            rationale=(
                "Applies to every device regardless of class or attributes - Section 3 "
                "conditions this on nothing device-specific."
            ),
            source_citation=self.source_citation,
            standards=[
                StandardApplicability(
                    standard_id="ISO 14971",
                    title="Medical devices - Application of risk management to medical devices",
                    note="The horizontal risk management standard cited across virtually all MDR guidance.",
                )
            ],
        )


class QualityManagementSystem(GSPRRequirementCheck):
    """Universal - quality management system.

    "Manufacturers of devices, other than investigational devices, shall
    establish, document, implement, maintain, keep up to date and
    continually improve a quality management system..." (Article 10(9))
    """

    requirement_id = "quality_management_system"
    title = "Quality management system"
    source_citation = "Regulation (EU) 2017/745, Article 10(9)"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=True,
            rationale=(
                "Applies to every device manufacturer other than for investigational "
                "devices, which this classifier does not model as a separate category "
                "- treat this as applying unless the device is purely for clinical "
                "investigation."
            ),
            source_citation=self.source_citation,
            standards=[
                StandardApplicability(
                    standard_id="ISO 13485",
                    title="Medical devices - Quality management systems - Requirements for regulatory purposes",
                )
            ],
        )


class ClinicalEvaluation(GSPRRequirementCheck):
    """Universal - clinical evaluation.

    "Confirmation of conformity with relevant general safety and
    performance requirements set out in Annex I... shall be based on
    clinical data providing sufficient clinical evidence..." (Article 61(1))
    """

    requirement_id = "clinical_evaluation"
    title = "Clinical evaluation"
    source_citation = "Regulation (EU) 2017/745, Article 61(1) and Annex XIV Part A"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        limitation = (
            "Article 61(3)(a) allows a literature-based equivalence review instead of "
            "a clinical investigation, so ISO 14155 does not automatically apply to "
            "every device just because clinical evaluation itself is universal - it "
            "governs clinical investigations specifically."
        )
        standards = [
            StandardApplicability(
                standard_id="ISO 14155",
                title="Clinical investigation of medical devices for human subjects - Good clinical practice",
                note="Applies if the evaluation route involves an actual clinical investigation, not to every device.",
            )
        ]
        note_extra = ""
        if device.is_implantable or classification.device_class in (DeviceClass.IIB, DeviceClass.III):
            note_extra = (
                " This device is implantable and/or Class IIb/III, where a clinical "
                "investigation is the common (not universally mandatory) route, and "
                "Class III / certain Class IIb devices may also involve the Article "
                "61(2) expert panel consultation before it."
            )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=True,
            rationale=(
                "Applies to every device regardless of class or attributes - Article "
                "61(1) conditions this on nothing device-specific." + note_extra
            ),
            source_citation=self.source_citation,
            standards=standards,
            limitation_note=limitation,
        )


class LabelingAndInstructionsForUse(GSPRRequirementCheck):
    """Universal - label and instructions for use.

    "Each device shall be accompanied by the information needed to
    identify the device and its manufacturer, and by any safety and
    performance information relevant to the user..." (Annex I, Section 23.1)
    """

    requirement_id = "labeling_and_ifu"
    title = "Label and instructions for use"
    source_citation = f"{_SOURCE_BASE}, Chapter III, Section 23"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        note_extra = ""
        if classification.device_class in (DeviceClass.I, DeviceClass.IIA):
            note_extra = (
                " Section 23.1(d) carves out an exception: instructions for use are "
                "not required for Class I and IIa devices that can be used safely "
                "without them - this device's Class "
                f"{classification.device_class.value} may qualify, but the label "
                "itself is still required either way."
            )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=True,
            rationale=(
                "Applies to every device regardless of class or attributes - Section "
                "23 conditions this on nothing device-specific." + note_extra
            ),
            source_citation=self.source_citation,
            standards=[
                StandardApplicability(
                    standard_id="ISO 15223-1",
                    title="Medical devices - Symbols to be used with information to be supplied by the manufacturer",
                ),
                StandardApplicability(
                    standard_id="ISO 20417",
                    title="Medical devices - Information to be supplied by the manufacturer",
                ),
            ],
        )


class Biocompatibility(GSPRRequirementCheck):
    """Triggered by any form of biological contact - chemical, physical
    and biological properties.

    "...Particular attention shall be paid to: ... (b) the compatibility
    between the materials and substances used and biological tissues,
    cells and body fluids..." (Annex I, Section 10.1(b); see also 10.2)
    """

    requirement_id = "biocompatibility"
    title = "Biological safety / biocompatibility"
    source_citation = f"{_SOURCE_BASE}, Sections 10.1(b) and 10.2"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = _has_biological_contact(device)
        limitation = (
            "ISO 10993-1 is a framework standard - it determines which further parts "
            "(e.g. -5 cytotoxicity, -10 irritation/sensitisation, -11 systemic "
            "toxicity) apply based on contact type, site and duration. This "
            "classifier does not attempt to select those further parts."
        )
        if device.contains_nanomaterial:
            limitation += (
                " Section 10.6 additionally requires special attention to "
                "nanomaterials specifically; ISO/TR 10993-22 provides guidance on "
                "nanomaterial biological evaluation."
            )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device contacts human tissue, cells, or body fluids (invasive, "
                "implantable, or otherwise in bodily contact per Section 10.1(b))."
                if applies
                else "No signal of biological contact was found on this device; Section 10.1(b)/10.2 do not apply."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="ISO 10993-1",
                        title="Biological evaluation of medical devices - Part 1: Evaluation and testing within a risk management process",
                    )
                ]
                if applies
                else []
            ),
            limitation_note=limitation if applies else "",
        )


class InfectionAndSterility(GSPRRequirementCheck):
    """Triggered by placed_on_market_sterile - infection and microbial
    contamination.

    "Devices labelled as sterile shall be processed, manufactured,
    packaged and, sterilised by means of appropriate, validated
    methods." (Annex I, Section 11.5)
    """

    requirement_id = "infection_and_sterility"
    title = "Infection and microbial contamination (sterility)"
    source_citation = f"{_SOURCE_BASE}, Section 11"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.placed_on_market_sterile
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device is placed on the market sterile, so Section 11's sterilisation "
                "and packaging-integrity requirements apply."
                if applies
                else "Device is not marked as placed on the market sterile; Section 11's sterility-specific points do not apply (11.1-11.2's general infection-control points still apply to all devices in principle but aren't tracked as a separate DeviceAttributes signal here)."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="ISO 11135",
                        title="Sterilization of health care products - Ethylene oxide",
                        note="One of three sterilisation-method standards - which applies depends on the method the manufacturer chooses, which this classifier does not know.",
                    ),
                    StandardApplicability(
                        standard_id="ISO 11137",
                        title="Sterilization of health care products - Radiation",
                        note="Method-dependent, see ISO 11135 note.",
                    ),
                    StandardApplicability(
                        standard_id="ISO 17665",
                        title="Sterilization of health care products - Moist heat",
                        note="Method-dependent, see ISO 11135 note.",
                    ),
                    StandardApplicability(
                        standard_id="ISO 11607",
                        title="Packaging for terminally sterilized medical devices",
                        note="Addresses Section 11.4/11.7's sterile-packaging-integrity requirement.",
                    ),
                ]
                if applies
                else []
            ),
        )


class BiologicalOriginMaterials(GSPRRequirementCheck):
    """Triggered by human/animal tissue or cell content.

    "For devices manufactured utilising tissues or cells of animal
    origin, or their derivatives... sourcing, processing, preservation,
    testing and handling... shall be carried out so as to provide safety
    for patients..." (Annex I, Section 13)
    """

    requirement_id = "biological_origin_materials"
    title = "Materials of biological origin (human/animal tissue or cells)"
    source_citation = f"{_SOURCE_BASE}, Section 13"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.contains_human_or_animal_tissue_or_cells
        standards: list[StandardApplicability] = []
        if applies:
            if device.tissue_origin == TissueOrigin.ANIMAL:
                standards.append(
                    StandardApplicability(
                        standard_id="ISO 22442",
                        title="Medical devices utilizing animal tissues and their derivatives",
                        note="Multi-part series (risk management, sourcing/handling, viral inactivation).",
                    )
                )
            elif device.tissue_origin == TissueOrigin.HUMAN:
                standards.append(
                    StandardApplicability(
                        standard_id="Directive 2004/23/EC",
                        title="EU tissues and cells directive (donation, procurement and testing)",
                        note="Not an ISO/IEC standard - Section 13.1(a) names this Directive directly, not a harmonised standard.",
                    )
                )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device contains or is manufactured using human or animal tissue/cells "
                "or their derivatives."
                if applies
                else "No human or animal tissue/cell content found; Section 13 does not apply."
            ),
            source_citation=self.source_citation,
            standards=standards,
        )


class IncorporatedMedicinalSubstances(GSPRRequirementCheck):
    """Triggered by an incorporated/co-administered medicinal substance.

    "...the quality, safety and usefulness of the substance which, if
    used separately, would be considered to be a medicinal product...
    shall be verified by analogy with the methods specified in Annex I
    to Directive 2001/83/EC..." (Annex I, Section 12.1)
    """

    requirement_id = "incorporated_medicinal_substances"
    title = "Incorporated or co-administered medicinal substances"
    source_citation = f"{_SOURCE_BASE}, Section 12"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = (
            device.administers_medicinal_product
            or device.contains_ancillary_medicinal_substance
            or device.composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin
        )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device administers, incorporates, or is composed of a substance that "
                "would be a medicinal product if used separately."
                if applies
                else "No incorporated/co-administered medicinal substance found; Section 12 does not apply."
            ),
            source_citation=self.source_citation,
            standards=[],
            limitation_note=(
                "This is not a 'standard' question - Section 12.1/12.2 point directly "
                "to Directive 2001/83/EC's own evaluation methods (by analogy), not to "
                "an ISO/IEC standard, so no StandardApplicability is listed."
                if applies
                else ""
            ),
        )


class SoftwareLifecycle(GSPRRequirementCheck):
    """Triggered by is_software - electronic programmable systems and
    software.

    "For devices that incorporate software or for software that are
    devices in themselves, the software shall be developed and
    manufactured in accordance with the state of the art taking into
    account the principles of development life cycle, risk management,
    including information security, verification and validation."
    (Annex I, Section 17.2)
    """

    requirement_id = "software_lifecycle"
    title = "Software lifecycle (development, risk management, security, V&V)"
    source_citation = f"{_SOURCE_BASE}, Section 17"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.is_software
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device is or incorporates software; Section 17's lifecycle, security "
                "and validation requirements apply."
                if applies
                else "Device is not flagged as software; Section 17 does not apply. Note: embedded/firmware software the extractor didn't separately flag would be missed here - see the module docstring."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="IEC 62304",
                        title="Medical device software - Software life cycle processes",
                    ),
                    StandardApplicability(
                        standard_id="IEC 82304-1",
                        title="Health software - Part 1: General requirements for product safety",
                        note="For standalone software placed on the market as a product in itself.",
                    ),
                    StandardApplicability(
                        standard_id="IEC 81001-5-1",
                        title="Health software and health IT systems safety, effectiveness and security - Part 5-1: Security - Activities in the product life cycle",
                        note="Addresses Section 17.2's 'information security' and 17.4/18.8's unauthorised-access requirements.",
                    ),
                ]
                if applies
                else []
            ),
        )


class ElectricalMechanicalSafetyAndEMC(GSPRRequirementCheck):
    """Triggered by is_active - active devices and devices connected to
    them, plus the general construction/mechanical-risk points.

    "Devices shall be designed and manufactured in such a way as to
    provide a level of intrinsic immunity to electromagnetic
    interference such that is adequate to enable them to operate as
    intended." (Annex I, Section 18.6; see also 14 and 20)
    """

    requirement_id = "electrical_mechanical_safety_emc"
    title = "Electrical, mechanical, thermal and EMC safety"
    source_citation = f"{_SOURCE_BASE}, Sections 14, 18 and 20"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.is_active
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device is active; Sections 14/18/20's electrical, mechanical, "
                "thermal and electromagnetic-compatibility requirements apply."
                if applies
                else "Device is not active; Sections 14/18/20's active-device-specific points do not apply."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="IEC 60601-1",
                        title="Medical electrical equipment - Part 1: General requirements for basic safety and essential performance",
                        note="Assumes an electrical energy source. Article 2(4) 'active device' also covers non-electrical energy sources (e.g. purely mechanical/spring-powered) that this classifier's is_active field cannot distinguish - a small minority of active devices would not need this standard.",
                    ),
                    StandardApplicability(
                        standard_id="IEC 60601-1-2",
                        title="Medical electrical equipment - Part 1-2: Electromagnetic disturbances",
                        note="Addresses Section 18.5/18.6 directly.",
                    ),
                ]
                if applies
                else []
            ),
        )


class RadiationProtection(GSPRRequirementCheck):
    """Triggered by any ionising-radiation-related field - protection
    against radiation.

    "Devices intended to emit ionizing radiation shall be designed and
    manufactured taking into account the requirements of the Directive
    2013/59/Euratom..." (Annex I, Section 16.4(a))
    """

    requirement_id = "radiation_protection"
    title = "Protection against radiation"
    source_citation = f"{_SOURCE_BASE}, Section 16"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = (
            device.supplies_ionising_radiation
            or device.emits_ionising_radiation_therapeutic
            or device.emits_ionising_radiation_diagnostic_or_interventional
            or device.is_xray_diagnostic_image_recording_device
        )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device supplies or emits ionising radiation; Section 16's radiation "
                "protection requirements apply, including compliance with Directive "
                "2013/59/Euratom (named directly in Section 16.4(a))."
                if applies
                else "No ionising-radiation signal found; Section 16 does not apply."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="IEC 60601-1-3",
                        title="Medical electrical equipment - Part 1-3: Radiation protection in diagnostic X-ray equipment",
                        note="One of several device-type-specific IEC 60601-2-xx/60601-1-x particular standards for radiation-emitting equipment - which one applies depends on the specific modality (diagnostic X-ray, CT, radiotherapy, nuclear medicine, etc.), which this classifier does not narrow further.",
                    )
                ]
                if applies
                else []
            ),
        )


class ActiveImplantableDevices(GSPRRequirementCheck):
    """Triggered by an active device that is also implantable -
    particular requirements for active implantable devices.

    "Active implantable devices shall be designed and manufactured in
    such a way as to remove or minimize as far as possible: (a) risks
    connected with the use of energy sources..." (Annex I, Section 19.1)
    """

    requirement_id = "active_implantable_devices"
    title = "Particular requirements for active implantable devices"
    source_citation = f"{_SOURCE_BASE}, Section 19"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.is_active_implantable_or_accessory or (device.is_active and device.is_implantable)
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device is both active and implantable; Section 19's particular "
                "requirements (energy source risks, identification/traceability) apply "
                "in addition to Sections 14/18/20."
                if applies
                else "Device is not both active and implantable; Section 19 does not apply."
            ),
            source_citation=self.source_citation,
            standards=(
                [
                    StandardApplicability(
                        standard_id="ISO 14708-1",
                        title="Implants for surgery - Active implantable medical devices - Part 1: General requirements for safety, marking and for information to be provided by the manufacturer",
                        note="Parent standard; particular parts exist for specific device types (e.g. -2 pacemakers, -3 neurostimulators, -4 implantable infusion pumps), device-type-dependent and not narrowed further.",
                    )
                ]
                if applies
                else []
            ),
        )


class MeasuringFunction(GSPRRequirementCheck):
    """Triggered by has_measuring_function - devices with a diagnostic or
    measuring function.

    "Diagnostic devices and devices with a measuring function, shall be
    designed and manufactured in such a way as to provide sufficient
    accuracy, precision and stability for their intended purpose..."
    (Annex I, Section 15.1)
    """

    requirement_id = "measuring_function"
    title = "Devices with a diagnostic or measuring function"
    source_citation = f"{_SOURCE_BASE}, Section 15"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = device.has_measuring_function
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device has a measuring function; Section 15's accuracy, precision "
                "and stability requirements apply."
                if applies
                else "Device does not have a measuring function; Section 15 does not apply."
            ),
            source_citation=self.source_citation,
            standards=[],
            limitation_note=(
                "Accuracy/precision requirements for measuring devices are typically "
                "demonstrated via a particular standard specific to what is being "
                "measured (e.g. a specific IEC 60601-2-xx part or a dedicated ISO "
                "standard for that measurement type) - this classifier cannot "
                "determine which from the available attributes, so none is named."
                if applies
                else ""
            ),
        )


class EnergyOrSubstanceDeliveryDevices(GSPRRequirementCheck):
    """Triggered by any energy- or substance-delivery field - protection
    against risks posed by devices supplying energy or substances.

    "Devices for supplying the patient with energy or substances shall
    be designed and constructed in such a way that the amount to be
    delivered can be set and maintained accurately enough to ensure the
    safety of the patient and of the user." (Annex I, Section 21.1)
    """

    requirement_id = "energy_or_substance_delivery"
    title = "Devices supplying energy or substances to the patient"
    source_citation = f"{_SOURCE_BASE}, Section 21"

    def evaluate(self, device: DeviceAttributes, classification: ClassificationResult) -> GSPRRequirement:
        applies = (
            device.administers_or_exchanges_energy
            or device.administers_or_removes_substances_to_from_body
            or device.channels_or_stores_for_infusion_administration_or_introduction
        )
        return GSPRRequirement(
            requirement_id=self.requirement_id,
            title=self.title,
            applies=applies,
            rationale=(
                "Device supplies energy or substances to/from the patient; Section "
                "21's dosing-accuracy and fail-safe requirements apply."
                if applies
                else "Device does not supply energy or substances to/from the patient; Section 21 does not apply."
            ),
            source_citation=self.source_citation,
            standards=[],
            limitation_note=(
                "Like measuring function, this is usually demonstrated via a "
                "device-type-specific particular standard (e.g. IEC 60601-2-24 for "
                "infusion pumps) that this classifier cannot determine from the "
                "available attributes."
                if applies
                else ""
            ),
        )


ALL_REQUIREMENTS: list[type[GSPRRequirementCheck]] = [
    RiskManagement,
    QualityManagementSystem,
    ClinicalEvaluation,
    LabelingAndInstructionsForUse,
    Biocompatibility,
    InfectionAndSterility,
    BiologicalOriginMaterials,
    IncorporatedMedicinalSubstances,
    SoftwareLifecycle,
    ElectricalMechanicalSafetyAndEMC,
    RadiationProtection,
    ActiveImplantableDevices,
    MeasuringFunction,
    EnergyOrSubstanceDeliveryDevices,
]
