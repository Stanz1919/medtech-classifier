"""EU MDR 2017/745 Annex VIII Classification Rules 1-22.

Every rule class below is written against the verbatim text saved in
docs/legal_sources/annex_viii_classification_rules.txt (fetched directly
from EUR-Lex, CELEX:32017R0745, retrieved 2026-08-02). Each class's
docstring quotes the operative part of the rule; the ``source_citation``
attribute points back to the specific Annex VIII section number.

Precedence within a rule: Annex VIII Chapter II, point 3.5 states that
"[i]f several rules, or if, within the same rule, several sub-rules,
apply to the same device based on the device's intended purpose, the
strictest rule and sub-rule resulting in the higher classification shall
apply." Every rule below is therefore implemented as a flat list of
(condition, resulting_class) candidates covering every clause of the
rule's text (its stated default included); the rule's outcome is the
highest-ranked class among whichever candidates evaluate true. This is a
direct, mechanical implementation of 3.5 - not a simplification - and it
is what lets a single generic helper (``_evaluate_candidates``) drive all
22 rules without rule-specific precedence code.

Cross-rule precedence (e.g. Rule 1 vs Rule 2, or Rule 6 vs Rule 9 both
matching the same device) is handled one level up, in
``rules_engine.eu_mdr.engine.EUMDRClassificationEngine``, using the same
3.5 "highest wins" logic across every rule's outcome.
"""

from __future__ import annotations

from typing import Optional

from rules_engine.base import ClassificationRule
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
    RuleOutcome,
    SoftwareDecisionImpact,
    StorageTarget,
    TissueOrigin,
    WoundContactPurpose,
    highest,
)

_SOURCE_BASE = (
    "Regulation (EU) 2017/745, Annex VIII, Chapter III"
    " (EUR-Lex CELEX:32017R0745, https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745)"
)

_ORAL_EAR_NASAL = {
    BodyOrificeSite.ORAL_CAVITY_TO_PHARYNX,
    BodyOrificeSite.EAR_CANAL_TO_EARDRUM,
    BodyOrificeSite.NASAL_CAVITY,
}


def _evaluate_candidates(
    candidates: list[tuple[bool, DeviceClass]]
) -> Optional[DeviceClass]:
    """Annex VIII 3.5: among all triggered candidates, the highest wins.

    Use this for rules whose clauses are independent/parallel (no single
    clause is a "default" that only applies when nothing else does).
    """
    matched = [cls for condition, cls in candidates if condition]
    return highest(*matched) if matched else None


def _evaluate_with_base(
    gate: bool,
    base_class: DeviceClass,
    exceptions: list[tuple[bool, DeviceClass]],
) -> Optional[DeviceClass]:
    """For rules drafted as "classified as BASE unless X, in which case Y":
    a matched exception replaces the base outcome, per the literal
    "unless X, in which case Y" wording - it does not merely compete with
    the base for the max. If several exceptions match simultaneously
    (e.g. a device is both a reusable surgical instrument -> I and has a
    biological effect -> IIb), Annex VIII 3.5's "highest wins" is applied
    among the matched exceptions only. The base is used solely as a
    fallback when the rule's gate is satisfied but no exception matched -
    this matters because some exceptions (e.g. Rule 6's reusable surgical
    instrument -> I, Rule 10's visible-spectrum illumination -> I) are
    *lower* than the base, and including the base unconditionally in a
    flat max would incorrectly suppress them.
    """
    if not gate:
        return None
    matched = [cls for condition, cls in exceptions if condition]
    return highest(*matched) if matched else base_class


class Rule1(ClassificationRule):
    """Rule 1 - non-invasive devices default to Class I.

    "All non-invasive devices are classified as class I, unless one of
    the rules set out hereinafter applies." (Annex VIII, 4.1)
    """

    rule_id = "Rule 1"
    source_citation = f"{_SOURCE_BASE}, Section 4.1"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        applies = device.invasiveness == Invasiveness.NON_INVASIVE
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=DeviceClass.I if applies else None,
            rationale=(
                "Device is non-invasive, so it defaults to Class I unless a "
                "more specific rule (2-4) applies and produces a higher class."
                if applies
                else "Device is not non-invasive; Rule 1 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule2(ClassificationRule):
    """Rule 2 - non-invasive devices channelling/storing for eventual
    infusion, administration or introduction into the body.

    "All non-invasive devices intended for channelling or storing blood,
    body liquids, cells or tissues, liquids or gases for the purpose of
    eventual infusion, administration or introduction into the body are
    classified as class IIa: - if they may be connected to a class IIa,
    class IIb or class III active device; or - if they are intended for
    use for channelling or storing blood or other body liquids or for
    storing organs, parts of organs or body cells and tissues, except for
    blood bags; blood bags are classified as class IIb. In all other
    cases, such devices are classified as class I." (Annex VIII, 4.2)
    """

    rule_id = "Rule 2"
    source_citation = f"{_SOURCE_BASE}, Section 4.2"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = (
            device.invasiveness == Invasiveness.NON_INVASIVE
            and device.channels_or_stores_for_infusion_administration_or_introduction
        )
        connected_to_active = gate and device.connected_to_active_device_class in (
            DeviceClass.IIA,
            DeviceClass.IIB,
            DeviceClass.III,
        )
        blood_bag = gate and device.storage_target == StorageTarget.BLOOD_BAGS
        blood_organ_storage = (
            gate
            and device.storage_target
            in (StorageTarget.BLOOD_OR_OTHER_BODY_LIQUIDS, StorageTarget.ORGANS_CELLS_TISSUES)
            and not blood_bag
        )
        catch_all = gate and not (connected_to_active or blood_bag or blood_organ_storage)

        candidates: list[tuple[bool, DeviceClass]] = [
            (connected_to_active, DeviceClass.IIA),
            (blood_organ_storage, DeviceClass.IIA),
            (blood_bag, DeviceClass.IIB),
            (catch_all, DeviceClass.I),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Non-invasive device channelling/storing blood, body liquids, "
                "cells, tissues, liquids or gases for eventual infusion, "
                "administration or introduction into the body."
                if gate
                else "Device is not a non-invasive channelling/storage device for eventual infusion/administration; Rule 2 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule3(ClassificationRule):
    """Rule 3 - non-invasive devices that modify biological/chemical
    composition, or are used in vitro with human cells/tissues/embryos.

    "All non-invasive devices intended for modifying the biological or
    chemical composition of human tissues or cells, blood, other body
    liquids or other liquids intended for implantation or administration
    into the body are classified as class IIb, unless the treatment for
    which the device is used consists of filtration, centrifugation or
    exchanges of gas, heat, in which case they are classified as class
    IIa. All non-invasive devices consisting of a substance or a mixture
    of substances intended to be used in vitro in direct contact with
    human cells, tissues or organs taken from the human body or used in
    vitro with human embryos before their implantation or administration
    into the body are classified as class III." (Annex VIII, 4.3)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    30-31 (docs/legal_sources/mdcg_2021-24_rule_3_examples.txt): IIb -
    haemodialysers, sperm-separation gradient media; IIa - particulate
    blood filtration, blood centrifugation for (auto)transfusion, blood
    warming/cooling in extracorporeal circulation; III - IVF/ART media
    without human albumin, organ transport/perfusion/storage substances.
    """

    rule_id = "Rule 3"
    source_citation = f"{_SOURCE_BASE}, Section 4.3"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        non_invasive = device.invasiveness == Invasiveness.NON_INVASIVE
        modifies = non_invasive and device.modifies_biological_or_chemical_composition
        in_vitro = non_invasive and device.in_vitro_direct_contact_with_cells_tissues_organs_or_embryos

        candidates: list[tuple[bool, DeviceClass]] = [
            (
                modifies
                and device.modification_treatment_type
                == ModificationTreatmentType.FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE,
                DeviceClass.IIA,
            ),
            (
                modifies
                and device.modification_treatment_type
                != ModificationTreatmentType.FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE,
                DeviceClass.IIB,
            ),
            (in_vitro, DeviceClass.III),
        ]
        result = _evaluate_candidates(candidates)
        applies = modifies or in_vitro
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=result,
            rationale=(
                "Non-invasive device modifying biological/chemical composition "
                "of human tissue/cells/blood/body liquids, and/or a substance "
                "used in vitro in direct contact with human cells/tissues/organs "
                "or embryos."
                if applies
                else "Device does not modify biological/chemical composition and is not an in-vitro substance device; Rule 3 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule4(ClassificationRule):
    """Rule 4 - devices in contact with injured skin or mucous membrane.

    "All non-invasive devices which come into contact with injured skin
    or mucous membrane are classified as: - class I if they are intended
    to be used as a mechanical barrier, for compression or for absorption
    of exudates; - class IIb if they are intended to be used principally
    for injuries to skin which have breached the dermis or mucous
    membrane and can only heal by secondary intent; - class IIa if they
    are principally intended to manage the micro-environment of injured
    skin or mucous membrane; and - class IIa in all other cases. This
    rule applies also to the invasive devices that come into contact with
    injured mucous membrane." (Annex VIII, 4.4)

    Precedence when a device could plausibly fit more than one bullet is
    explicitly confirmed - not left to interpretation - by official
    guidance: MDCG 2021-24 Rev.1, "Guidance on classification of medical
    devices" (pages 32-33): "Most dressings that are intended for a use
    that falls under class IIa or IIb also perform functions that are in
    class I, e.g. that of a mechanical barrier. Such devices are
    nevertheless classified according to their intended use in the higher
    class." This is exactly the max-of-matched-bullets logic implemented
    below, so it is not flagged as an engine-level ambiguity.

    The genuine judgement call MDCG identifies is upstream of this rule,
    at the point of determining the manufacturer's *intended purpose*
    from a device description: "it is impossible to say a priori that a
    particular type of dressing belongs to a given class without knowing
    its intended use as defined by the manufacturer." That is a Phase 2
    (extraction) concern, not something this rule's logic can resolve -
    see docs/CLARIFICATIONS_RULE_4.md.
    """

    rule_id = "Rule 4"
    source_citation = f"{_SOURCE_BASE}, Section 4.4"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        # Trailing sentence extends this rule to invasive devices touching
        # injured mucous membrane, so the gate is the contact flag itself,
        # not an invasiveness check.
        gate = device.contacts_injured_skin_or_mucous_membrane

        candidates: list[tuple[bool, DeviceClass]] = [
            (
                gate
                and device.wound_contact_purpose
                == WoundContactPurpose.MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION,
                DeviceClass.I,
            ),
            (
                gate
                and device.wound_contact_purpose
                == WoundContactPurpose.BREACHED_DERMIS_SECONDARY_INTENT_HEALING,
                DeviceClass.IIB,
            ),
            (
                gate and device.wound_contact_purpose == WoundContactPurpose.MANAGE_MICROENVIRONMENT,
                DeviceClass.IIA,
            ),
            (
                gate
                and device.wound_contact_purpose
                not in (
                    WoundContactPurpose.MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION,
                    WoundContactPurpose.BREACHED_DERMIS_SECONDARY_INTENT_HEALING,
                    WoundContactPurpose.MANAGE_MICROENVIRONMENT,
                ),
                DeviceClass.IIA,
            ),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                f"Device contacts injured skin/mucous membrane; wound-contact "
                f"purpose '{device.wound_contact_purpose.value}' determines the class."
                if gate
                else "Device does not contact injured skin or mucous membrane; Rule 4 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule5(ClassificationRule):
    """Rule 5 - invasive devices w.r.t. body orifices (non-surgical).

    "All invasive devices with respect to body orifices, other than
    surgically invasive devices, which are not intended for connection to
    an active device or which are intended for connection to a class I
    active device are classified as: - class I if... transient use; -
    class IIa if... short-term use, except if... oral cavity as far as
    the pharynx, in an ear canal up to the ear drum or in the nasal
    cavity, in which case... class I; and - class IIb if... long-term
    use, except if... oral cavity..., ear canal..., or nasal cavity...
    and are not liable to be absorbed by the mucous membrane, in which
    case... class IIa. All invasive devices with respect to body
    orifices, other than surgically invasive devices, intended for
    connection to a class IIa, class IIb or class III active device, are
    classified as class IIa." (Annex VIII, 5.1)
    """

    rule_id = "Rule 5"
    source_citation = f"{_SOURCE_BASE}, Section 5.1"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        is_body_orifice_invasive = device.invasiveness == Invasiveness.INVASIVE_BODY_ORIFICE
        not_connected_or_class_i = device.connected_to_active_device_class in (None, DeviceClass.I)
        duration_gate = is_body_orifice_invasive and not_connected_or_class_i

        orifice_exempt = device.body_orifice_site in _ORAL_EAR_NASAL

        connected_to_higher_active = is_body_orifice_invasive and device.connected_to_active_device_class in (
            DeviceClass.IIA,
            DeviceClass.IIB,
            DeviceClass.III,
        )

        candidates: list[tuple[bool, DeviceClass]] = [
            (duration_gate and device.duration == Duration.TRANSIENT, DeviceClass.I),
            (
                duration_gate and device.duration == Duration.SHORT_TERM and orifice_exempt,
                DeviceClass.I,
            ),
            (
                duration_gate and device.duration == Duration.SHORT_TERM and not orifice_exempt,
                DeviceClass.IIA,
            ),
            (
                duration_gate
                and device.duration == Duration.LONG_TERM
                and orifice_exempt
                and not device.liable_to_be_absorbed_by_mucous_membrane,
                DeviceClass.IIA,
            ),
            (
                duration_gate
                and device.duration == Duration.LONG_TERM
                and not (orifice_exempt and not device.liable_to_be_absorbed_by_mucous_membrane),
                DeviceClass.IIB,
            ),
            (connected_to_higher_active, DeviceClass.IIA),
        ]
        result = _evaluate_candidates(candidates)
        applies = duration_gate or connected_to_higher_active
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=result,
            rationale=(
                f"Non-surgical body-orifice-invasive device, duration "
                f"'{device.duration.value}', orifice site "
                f"'{device.body_orifice_site.value}'."
                if applies
                else "Device is not a non-surgical body-orifice-invasive device (or Rule 6-8 covers it instead); Rule 5 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule6(ClassificationRule):
    """Rule 6 - surgically invasive devices, transient use.

    "All surgically invasive devices intended for transient use are
    classified as class IIa unless they: - are intended specifically to
    control, diagnose, monitor or correct a defect of the heart or of the
    central circulatory system through direct contact with those parts of
    the body, in which case... class III; - are reusable surgical
    instruments, in which case... class I; - are intended specifically
    for use in direct contact with the heart or central circulatory
    system or the central nervous system, in which case... class III; -
    are intended to supply energy in the form of ionising radiation in
    which case... class IIb; - have a biological effect or are wholly or
    mainly absorbed in which case... class IIb; or - are intended to
    administer medicinal products by means of a delivery system, if such
    administration... is done in a manner that is potentially hazardous
    taking account of the mode of application, in which case... class
    IIb." (Annex VIII, 5.2)
    """

    rule_id = "Rule 6"
    source_citation = f"{_SOURCE_BASE}, Section 5.2"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = (
            device.invasiveness == Invasiveness.SURGICALLY_INVASIVE
            and device.duration == Duration.TRANSIENT
            and not device.is_implantable
        )
        exceptions: list[tuple[bool, DeviceClass]] = [
            (device.contacts_heart_or_central_circulatory_system, DeviceClass.III),
            (device.is_reusable_surgical_instrument, DeviceClass.I),
            (
                device.contacts_heart_or_central_circulatory_system or device.contacts_central_nervous_system,
                DeviceClass.III,
            ),
            (device.supplies_ionising_radiation, DeviceClass.IIB),
            (device.has_biological_effect_or_wholly_mainly_absorbed, DeviceClass.IIB),
            (
                device.administers_medicinal_product and device.administration_potentially_hazardous,
                DeviceClass.IIB,
            ),
        ]
        result = _evaluate_with_base(gate, DeviceClass.IIA, exceptions)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Surgically invasive device intended for transient use "
                "(non-implantable)."
                if gate
                else "Device is not a non-implantable, transient-use surgically invasive device; Rule 6 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule7(ClassificationRule):
    """Rule 7 - surgically invasive devices, short-term use.

    "All surgically invasive devices intended for short-term use are
    classified as class IIa unless they: - are intended specifically to
    control, diagnose, monitor or correct a defect of the heart or of the
    central circulatory system through direct contact..., in which
    case... class III; - are intended specifically for use in direct
    contact with the heart or central circulatory system or the central
    nervous system, in which case... class III; - are intended to supply
    energy in the form of ionizing radiation in which case... class IIb;
    - have a biological effect or are wholly or mainly absorbed in which
    case... class III; - are intended to undergo chemical change in the
    body in which case... class IIb, except if the devices are placed in
    the teeth; or - are intended to administer medicines, in which
    case... class IIb." (Annex VIII, 5.3)
    """

    rule_id = "Rule 7"
    source_citation = f"{_SOURCE_BASE}, Section 5.3"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = (
            device.invasiveness == Invasiveness.SURGICALLY_INVASIVE
            and device.duration == Duration.SHORT_TERM
            and not device.is_implantable
        )
        exceptions: list[tuple[bool, DeviceClass]] = [
            (device.contacts_heart_or_central_circulatory_system, DeviceClass.III),
            (
                device.contacts_heart_or_central_circulatory_system or device.contacts_central_nervous_system,
                DeviceClass.III,
            ),
            (device.supplies_ionising_radiation, DeviceClass.IIB),
            (device.has_biological_effect_or_wholly_mainly_absorbed, DeviceClass.III),
            (
                device.undergoes_chemical_change_in_body and not device.placed_in_teeth,
                DeviceClass.IIB,
            ),
            (device.administers_medicinal_product, DeviceClass.IIB),
        ]
        result = _evaluate_with_base(gate, DeviceClass.IIA, exceptions)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Surgically invasive device intended for short-term use "
                "(non-implantable)."
                if gate
                else "Device is not a non-implantable, short-term-use surgically invasive device; Rule 7 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule8(ClassificationRule):
    """Rule 8 - implantable devices and long-term surgically invasive devices.

    "All implantable devices and long-term surgically invasive devices
    are classified as class IIb unless they: - are intended to be placed
    in the teeth, in which case... class IIa; - are intended to be used
    in direct contact with the heart, the central circulatory system or
    the central nervous system, in which case... class III; - have a
    biological effect or are wholly or mainly absorbed, in which case...
    class III; - are intended to undergo chemical change in the body in
    which case... class III, except if the devices are placed in the
    teeth; - are intended to administer medicinal products, in which
    case... class III; - are active implantable devices or their
    accessories, in which cases... class III; - are breast implants or
    surgical meshes, in which cases... class III; - are total or partial
    joint replacements, in which case... class III, with the exception of
    ancillary components such as screws, wedges, plates and instruments;
    or - are spinal disc replacement implants or are implantable devices
    that come into contact with the spinal column, in which case... class
    III with the exception of components such as screws, wedges, plates
    and instruments." (Annex VIII, 5.4)

    Two nuances confirmed against official guidance - MDCG 2021-24 Rev.1,
    "Guidance on classification of medical devices" (pages 38-41; see
    docs/legal_sources/mdcg_2021-24_rule_8_implants.txt and
    docs/CLARIFICATIONS_RULE_8.md):

    1. "Ancillary components" has real named examples, not just abstract
       wording: MDCG lists **pedicle screws** and, per its Note 7, **hooks
       that fix rods on the spinal column** as staying at the Rule 8 base
       class (IIb) rather than escalating to III alongside the joint/spinal
       implant they're part of. But MDCG's Note 1 is explicit that this is
       NOT a blanket "screws are always ancillary" rule: "This does not
       imply classification of all sutures, staples, dental fillings,
       dental braces, tooth crowns, screws, wedges, plates, wires, pins,
       clips and connectors as class IIb. Such devices must be classified
       in their own right according to their intended purpose and the
       applicable rules." Each component still needs its own intended-
       purpose classification - the carve-out just means fixation hardware
       doesn't automatically inherit the III of the implant it's attached
       to.
    2. The "placed in the teeth" -> IIa exception is narrower than it
       sounds. MDCG's Note 4: "Implants without bioactive coatings
       intended to secure teeth or prostheses to the maxillary or
       mandibular bones are in Class IIb following the general rule."
       I.e. a dental implant *post* anchored in the jawbone stays at the
       Rule 8 base class (IIb) - MDCG lists "Dental implants and
       abutments" as a IIb example, not IIa. Only things genuinely placed
       *within* tooth structure (fillings, crowns, bridges, dental
       alloys/ceramics/polymers) get the IIa exception. The
       `placed_in_teeth` attribute should be populated accordingly.
    """

    rule_id = "Rule 8"
    source_citation = f"{_SOURCE_BASE}, Section 5.4"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = device.is_implantable or (
            device.invasiveness == Invasiveness.SURGICALLY_INVASIVE and device.duration == Duration.LONG_TERM
        )
        joint_exception = device.is_joint_replacement and not device.is_ancillary_component
        spinal_exception = (
            device.is_spinal_disc_replacement_or_contacts_spinal_column and not device.is_ancillary_component
        )
        exceptions: list[tuple[bool, DeviceClass]] = [
            (device.placed_in_teeth, DeviceClass.IIA),
            (
                device.contacts_heart_or_central_circulatory_system or device.contacts_central_nervous_system,
                DeviceClass.III,
            ),
            (device.has_biological_effect_or_wholly_mainly_absorbed, DeviceClass.III),
            (
                device.undergoes_chemical_change_in_body and not device.placed_in_teeth,
                DeviceClass.III,
            ),
            (device.administers_medicinal_product, DeviceClass.III),
            (device.is_active_implantable_or_accessory, DeviceClass.III),
            (device.is_breast_implant_or_surgical_mesh, DeviceClass.III),
            (joint_exception, DeviceClass.III),
            (spinal_exception, DeviceClass.III),
        ]
        result = _evaluate_with_base(gate, DeviceClass.IIB, exceptions)
        ambiguous = gate and (
            (device.is_joint_replacement and device.is_ancillary_component)
            or (device.is_spinal_disc_replacement_or_contacts_spinal_column and device.is_ancillary_component)
        )
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Implantable device or long-term surgically invasive device."
                if gate
                else "Device is not implantable and not a long-term surgically invasive device; Rule 8 does not apply."
            ),
            source_citation=self.source_citation,
            ambiguous=ambiguous,
            ambiguous_note=(
                "Device is flagged as an 'ancillary component' (screw, wedge, "
                "plate, instrument) of a joint replacement or spinal implant "
                "system, which the rule text exempts from Class III. MDCG "
                "2021-24 confirms real examples of this carve-out (pedicle "
                "screws; hooks fixing rods to the spinal column, per its Note "
                "7) - so this is not pure guesswork - but its Note 1 is "
                "explicit that there is no blanket rule: each component must "
                "still be classified 'in their own right according to their "
                "intended purpose and the applicable rules'. Whether THIS "
                "component is genuinely fixation hardware versus a load-"
                "bearing/functional part of the implant is a fact-specific "
                "judgement; see docs/CLARIFICATIONS_RULE_8.md."
                if ambiguous
                else None
            ),
        )


class Rule9(ClassificationRule):
    """Rule 9 - active therapeutic devices.

    "All active therapeutic devices intended to administer or exchange
    energy are classified as class IIa unless their characteristics are
    such that they may administer energy to or exchange energy with the
    human body in a potentially hazardous way..., in which case... class
    IIb. All active devices intended to control or monitor the
    performance of active therapeutic class IIb devices, or intended
    directly to influence the performance of such devices are classified
    as class IIb. All active devices intended to emit ionizing radiation
    for therapeutic purposes, including devices which control or monitor
    such devices, or which directly influence their performance, are
    classified as class IIb. All active devices that are intended for
    controlling, monitoring or directly influencing the performance of
    active implantable devices are classified as class III."
    (Annex VIII, 6.1)
    """

    rule_id = "Rule 9"
    source_citation = f"{_SOURCE_BASE}, Section 6.1"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        energy_gate = (
            device.is_active
            and device.active_type == ActiveDeviceType.THERAPEUTIC
            and device.administers_or_exchanges_energy
        )
        controls_iib = device.is_active and device.controls_monitors_or_influences_therapeutic_class_iib_device
        emits_therapeutic_radiation = device.is_active and device.emits_ionising_radiation_therapeutic
        controls_active_implantable = device.is_active and device.controls_monitors_or_influences_active_implantable_device

        candidates: list[tuple[bool, DeviceClass]] = [
            (energy_gate, DeviceClass.IIA),
            (energy_gate and device.energy_exchange_potentially_hazardous, DeviceClass.IIB),
            (controls_iib, DeviceClass.IIB),
            (emits_therapeutic_radiation, DeviceClass.IIB),
            (controls_active_implantable, DeviceClass.III),
        ]
        result = _evaluate_candidates(candidates)
        applies = energy_gate or controls_iib or emits_therapeutic_radiation or controls_active_implantable
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=result,
            rationale=(
                "Active therapeutic device administering/exchanging energy, "
                "and/or controlling/monitoring another active therapeutic or "
                "active implantable device, and/or emitting therapeutic "
                "ionising radiation."
                if applies
                else "Device is not an active therapeutic energy device covered by Rule 9; Rule 9 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule10(ClassificationRule):
    """Rule 10 - active devices for diagnosis and monitoring.

    "Active devices intended for diagnosis and monitoring are classified
    as class IIa: - if they are intended to supply energy which will be
    absorbed by the human body, except for devices intended to illuminate
    the patient's body, in the visible spectrum, in which case... class
    I; - if they are intended to image in vivo distribution of
    radiopharmaceuticals; or - if they are intended to allow direct
    diagnosis or monitoring of vital physiological processes, unless they
    are specifically intended for monitoring of vital physiological
    parameters and the nature of variations of those parameters is such
    that it could result in immediate danger to the patient..., or they
    are intended for diagnosis in clinical situations where the patient
    is in immediate danger, in which cases... class IIb. Active devices
    intended to emit ionizing radiation and intended for diagnostic or
    therapeutic radiology, including interventional radiology devices and
    devices which control or monitor such devices, or which directly
    influence their performance, are classified as class IIb."
    (Annex VIII, 6.2)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    44-45 (docs/legal_sources/mdcg_2021-24_rule_10_examples.txt): IIa -
    MRI, diagnostic ultrasound, ECG/EEG, electronic thermometers/blood
    pressure monitors; I - examination lamps, surgical illumination
    microscopes; IIb - blood gas analysers in open-heart surgery, apnoea
    monitors (incl. home use), ICU multi-parameter patient monitors,
    diagnostic X-ray machines, CT scanners. MDCG's Note 3 is a useful
    context-dependence rule of thumb: continuous vital-parameter
    surveillance in anaesthesia/ICU/emergency care is IIb, while routine
    checkup/self-monitoring readings of the same parameters are IIa.
    """

    rule_id = "Rule 10"
    source_citation = f"{_SOURCE_BASE}, Section 6.2"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        diag_gate = device.is_active and device.active_type == ActiveDeviceType.DIAGNOSTIC_MONITORING
        radiology_gate = device.is_active and device.emits_ionising_radiation_diagnostic_or_interventional

        energy_absorbed = diag_gate and device.diagnostic_supplies_energy_absorbed_by_body
        illumination_only = energy_absorbed and device.diagnostic_illuminates_patient_visible_spectrum_only
        direct_diag = diag_gate and device.diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes
        immediate_danger = direct_diag and device.diagnostic_variation_could_cause_immediate_danger

        candidates: list[tuple[bool, DeviceClass]] = [
            (energy_absorbed and not illumination_only, DeviceClass.IIA),
            (illumination_only, DeviceClass.I),
            (diag_gate and device.diagnostic_images_in_vivo_radiopharmaceutical_distribution, DeviceClass.IIA),
            (direct_diag and not immediate_danger, DeviceClass.IIA),
            (immediate_danger, DeviceClass.IIB),
            (radiology_gate, DeviceClass.IIB),
        ]
        result = _evaluate_candidates(candidates)
        applies = diag_gate or radiology_gate
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=result,
            rationale=(
                "Active diagnostic/monitoring device and/or a device emitting "
                "ionising radiation for diagnostic/interventional radiology."
                if applies
                else "Device is not an active diagnostic/monitoring or diagnostic-radiology device; Rule 10 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule11(ClassificationRule):
    """Rule 11 - software.

    "Software intended to provide information which is used to take
    decisions with diagnosis or therapeutic purposes is classified as
    class IIa, except if such decisions have an impact that may cause: -
    death or an irreversible deterioration of a person's state of
    health, in which case it is in class III; or - a serious
    deterioration of a person's state of health or a surgical
    intervention, in which case it is classified as class IIb. Software
    intended to monitor physiological processes is classified as class
    IIa, except if it is intended for monitoring of vital physiological
    parameters, where the nature of variations of those parameters is
    such that it could result in immediate danger to the patient, in
    which case it is classified as class IIb. All other software is
    classified as class I." (Annex VIII, 6.3)

    Verified against official guidance - MDCG 2021-24 Rev.1, "Guidance on
    classification of medical devices" (pages 46-47; see
    docs/legal_sources/mdcg_2021-24_rule_11_software.txt and
    docs/CLARIFICATIONS_RULE_11.md), which itself points to the dedicated
    MDCG 2019-11 "Qualification and classification of software" guidance
    for further detail (that document has not separately been fetched -
    only what MDCG 2021-24 quotes from it is relied on here).

    Two things confirmed from the real text, not assumed:
    1. Severity is explicitly context-dependent, not a property of the
       software alone - MDCG's Note 2: "it is needed to consider the
       intended purpose, intended population..., context of use (e.g.
       intensive care, emergency care, home use)... as well as of the
       possible decisions to be taken." The same monitoring algorithm can
       be IIa (home use) or IIb (ICU) depending on context - this is why
       `software_monitors_vital_parameters_with_immediate_danger_potential`
       is modelled as a separate flag rather than inferred purely from
       what is being monitored.
    2. Software driving a physical device is scoped OUT of Rule 11
       entirely by Annex VIII Chapter II, point 3.3 ("Software, which
       drives a device or influences the use of a device, shall fall
       within the same class as the device") - MDCG's Note 3 restates
       this. **Implemented**: when
       ``device.drives_or_influences_device_class`` is set, this rule
       short-circuits to that class directly (citing 3.3) instead of
       evaluating its own decision-support/monitoring criteria - e.g.
       firmware driving a Class IIb infusion pump inherits IIb, even if
       Rule 11's own criteria would otherwise compute something else for
       the firmware in isolation. This was a genuine gap found while
       researching this rule (not present in Phase 1) - see
       docs/CLARIFICATIONS_RULE_11.md.
    """

    rule_id = "Rule 11"
    source_citation = f"{_SOURCE_BASE}, Section 6.3"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        if not device.is_software:
            return RuleOutcome(
                rule_id=self.rule_id,
                applies=False,
                device_class=None,
                rationale="Device is not software; Rule 11 does not apply.",
                source_citation=self.source_citation,
            )

        if device.drives_or_influences_device_class is not None:
            # Annex VIII Chapter II, point 3.3 - not Rule 11 itself, but the
            # implementing rule governing it: software driving or
            # influencing another device inherits that device's class
            # outright. Rule 11's own decision-support/monitoring criteria
            # are not evaluated in this case.
            driven_class = device.drives_or_influences_device_class
            return RuleOutcome(
                rule_id=self.rule_id,
                applies=True,
                device_class=driven_class,
                rationale=(
                    f"Software drives or influences the use of another "
                    f"device; per Annex VIII Chapter II, point 3.3, it "
                    f"inherits that device's class (Class {driven_class.value}) "
                    f"rather than being independently classified under "
                    f"Rule 11's decision-support/monitoring criteria."
                ),
                source_citation=(
                    "Regulation (EU) 2017/745, Annex VIII, Chapter II, point 3.3"
                    " (EUR-Lex CELEX:32017R0745); confirmed by MDCG 2021-24 Rev.1"
                    " Note 3 to Rule 11, p. 47"
                ),
            )

        decision_support = device.software_decision_impact != SoftwareDecisionImpact.NOT_APPLICABLE
        monitoring = device.software_monitors_physiological_processes
        other_software = not decision_support and not monitoring

        candidates: list[tuple[bool, DeviceClass]] = [
            (
                decision_support and device.software_decision_impact == SoftwareDecisionImpact.OTHER_IMPACT,
                DeviceClass.IIA,
            ),
            (
                decision_support
                and device.software_decision_impact
                == SoftwareDecisionImpact.SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION,
                DeviceClass.IIB,
            ),
            (
                decision_support
                and device.software_decision_impact == SoftwareDecisionImpact.DEATH_OR_IRREVERSIBLE_DETERIORATION,
                DeviceClass.III,
            ),
            (
                monitoring and not device.software_monitors_vital_parameters_with_immediate_danger_potential,
                DeviceClass.IIA,
            ),
            (
                monitoring and device.software_monitors_vital_parameters_with_immediate_danger_potential,
                DeviceClass.IIB,
            ),
            (other_software, DeviceClass.I),
        ]
        result = _evaluate_candidates(candidates)
        severity_flagged = decision_support and device.software_decision_impact in (
            SoftwareDecisionImpact.SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION,
            SoftwareDecisionImpact.DEATH_OR_IRREVERSIBLE_DETERIORATION,
        )
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=True,
            device_class=result,
            rationale=(
                f"Software device; decision-support impact "
                f"'{device.software_decision_impact.value}', monitors "
                f"physiological processes: {monitoring}."
            ),
            source_citation=self.source_citation,
            ambiguous=severity_flagged,
            ambiguous_note=(
                "Classifying decision-support software by the severity of harm "
                "its output *could* cause is confirmed by MDCG 2021-24's own "
                "Note 2 to be context-dependent - the same software can shift "
                "class based on intended population, clinical setting (home vs. "
                "ICU/emergency), and the decisions actually being informed, not "
                "just its function in isolation. Real examples from MDCG "
                "2021-24 (pp. 46-47): image-analysis stroke diagnosis software "
                "-> III; a heartbeat-arrhythmia-detection app -> IIb; a "
                "chemotherapy-option ranking tool for clinicians -> IIa. "
                "Assigning the correct tier from a free-text description is a "
                "genuine judgement call for Phase 2's extractor; see "
                "docs/CLARIFICATIONS_RULE_11.md."
                if severity_flagged
                else None
            ),
        )


class Rule12(ClassificationRule):
    """Rule 12 - active devices administering/removing substances.

    "All active devices intended to administer and/or remove medicinal
    products, body liquids or other substances to or from the body are
    classified as class IIa, unless this is done in a manner that is
    potentially hazardous, taking account of the nature of the substances
    involved, of the part of the body concerned and of the mode of
    application in which case they are classified as class IIb."
    (Annex VIII, 6.4)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, page 48
    (docs/legal_sources/mdcg_2021-24_rule_12_examples.txt): IIa -
    suction pumps, feeding pumps, jet injectors for vaccination,
    elastomeric/balloon infusion pumps; IIb - infusion pumps, ventilators,
    anaesthesia machines, dialysis equipment, heart-lung machine blood
    pumps, hyperbaric chambers.
    """

    rule_id = "Rule 12"
    source_citation = f"{_SOURCE_BASE}, Section 6.4"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = device.is_active and device.administers_or_removes_substances_to_from_body
        candidates: list[tuple[bool, DeviceClass]] = [
            (gate and not device.administration_or_removal_potentially_hazardous, DeviceClass.IIA),
            (gate and device.administration_or_removal_potentially_hazardous, DeviceClass.IIB),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Active device administering and/or removing medicinal "
                "products, body liquids or other substances to/from the body."
                if gate
                else "Device does not administer or remove substances to/from the body; Rule 12 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule13(ClassificationRule):
    """Rule 13 - residual catch-all for active devices.

    "All other active devices are classified as class I." (Annex VIII, 6.5)

    Modelling note: the legal text defines this as "not covered by Rules
    9-12", which is a property of the *device* as a whole, not something
    a single rule class can determine on its own. This implementation
    gates on ``active_type == ActiveDeviceType.OTHER_ACTIVE``, an explicit
    bucket in the attribute model reserved for exactly this residual
    case. The extractor (or a human filling in the CLI harness) is
    responsible for only setting this bucket when Rules 9-12 genuinely do
    not describe the device.

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    48-49 (docs/legal_sources/mdcg_2021-24_rule_13_examples.txt): electric
    wheelchairs, dental curing lights, electric hospital beds, patient
    hoists, dental patient chairs - all Class I.
    """

    rule_id = "Rule 13"
    source_citation = f"{_SOURCE_BASE}, Section 6.5"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        applies = device.is_active and device.active_type == ActiveDeviceType.OTHER_ACTIVE
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=DeviceClass.I if applies else None,
            rationale=(
                "Active device not falling under Rules 9-12 (therapeutic "
                "energy exchange, diagnosis/monitoring, software, or "
                "substance administration/removal)."
                if applies
                else "Device is not an active device in the residual 'other' bucket; Rule 13 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule14(ClassificationRule):
    """Rule 14 - devices incorporating a medicinal substance.

    "All devices incorporating, as an integral part, a substance which,
    if used separately, can be considered to be a medicinal product...,
    including a medicinal product derived from human blood or human
    plasma..., and that has an action ancillary to that of the devices,
    are classified as class III." (Annex VIII, 7.1)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    49-50 (docs/legal_sources/mdcg_2021-24_rule_14_examples.txt): bone
    cement with antibiotics, condoms with spermicide, heparin-coated
    catheters, drug-eluting stents, IUDs containing copper or silver,
    blood bags incorporating heparin. MDCG's own worked cross-rule
    example: "IVF cell media with human albumin are in class III
    according to Rule 14 and Rule 3. (Rule 14 applies, being the
    strictest, according to MDR, Annex VIII, chapter II, point 3.5.)" -
    direct confirmation this engine's cross-rule "highest wins" logic
    matches official practice.
    """

    rule_id = "Rule 14"
    source_citation = f"{_SOURCE_BASE}, Section 7.1"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        applies = device.contains_ancillary_medicinal_substance
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=DeviceClass.III if applies else None,
            rationale=(
                "Device incorporates, as an integral part, a substance with an "
                "action ancillary to the device that would itself qualify as a "
                "medicinal product."
                if applies
                else "Device does not incorporate an ancillary medicinal substance; Rule 14 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule15(ClassificationRule):
    """Rule 15 - contraception / STI prevention devices.

    "All devices used for contraception or prevention of the transmission
    of sexually transmitted diseases are classified as class IIb, unless
    they are implantable or long term invasive devices, in which case
    they are classified as class III." (Annex VIII, 7.2)
    """

    rule_id = "Rule 15"
    source_citation = f"{_SOURCE_BASE}, Section 7.2"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = device.is_contraceptive_or_sti_prevention
        long_term_or_implantable = device.is_implantable or (
            device.invasiveness == Invasiveness.SURGICALLY_INVASIVE and device.duration == Duration.LONG_TERM
        )
        candidates: list[tuple[bool, DeviceClass]] = [
            (gate and not long_term_or_implantable, DeviceClass.IIB),
            (gate and long_term_or_implantable, DeviceClass.III),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Device is used for contraception or prevention of STI "
                "transmission."
                if gate
                else "Device is not a contraception/STI-prevention device; Rule 15 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule16(ClassificationRule):
    """Rule 16 - contact lens care and device disinfection/sterilisation.

    "All devices intended specifically to be used for disinfecting,
    cleaning, rinsing or, where appropriate, hydrating contact lenses are
    classified as class IIb. All devices intended specifically to be used
    for disinfecting or sterilising medical devices are classified as
    class IIa, unless they are disinfecting solutions or
    washer-disinfectors intended specifically to be used for disinfecting
    invasive devices, as the end point of processing, in which case they
    are classified as class IIb. This rule does not apply to devices that
    are intended to clean devices other than contact lenses by means of
    physical action only." (Annex VIII, 7.3)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    51-52 (docs/legal_sources/mdcg_2021-24_rule_16_examples.txt): IIb -
    contact lens storing solutions; IIa - disinfecting solutions for
    non-invasive medical devices, sterilisers for medical devices in a
    medical environment; IIb - washer-disinfectors for endoscopes/
    invasive devices at end of processing, disinfectants for
    haemodialysis fluid pathways; carve-out - brushes/ultrasonic devices
    for mechanical cleaning of non-lens devices.
    """

    rule_id = "Rule 16"
    source_citation = f"{_SOURCE_BASE}, Section 7.3"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        target = device.disinfect_clean_target
        candidates: list[tuple[bool, DeviceClass]] = [
            (target == DisinfectCleanTarget.CONTACT_LENSES, DeviceClass.IIB),
            (target == DisinfectCleanTarget.INVASIVE_DEVICE_END_POINT, DeviceClass.IIB),
            (target == DisinfectCleanTarget.OTHER_MEDICAL_DEVICE, DeviceClass.IIA),
        ]
        result = _evaluate_candidates(candidates)
        applies = result is not None
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=result,
            rationale=(
                f"Device is specifically intended to disinfect/clean/rinse/"
                f"hydrate: target category '{target.value}'."
                if applies
                else (
                    "Device only cleans non-contact-lens devices by physical "
                    "action only (explicit carve-out), or is not a "
                    "disinfecting/cleaning device at all; Rule 16 does not apply."
                )
            ),
            source_citation=self.source_citation,
        )


class Rule17(ClassificationRule):
    """Rule 17 - X-ray diagnostic image recording devices.

    "Devices specifically intended for recording of diagnostic images
    generated by X-ray radiation are classified as class IIa."
    (Annex VIII, 7.4)
    """

    rule_id = "Rule 17"
    source_citation = f"{_SOURCE_BASE}, Section 7.4"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        applies = device.is_xray_diagnostic_image_recording_device
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=DeviceClass.IIA if applies else None,
            rationale=(
                "Device is specifically intended to record diagnostic images "
                "generated by X-ray radiation."
                if applies
                else "Device is not an X-ray diagnostic image recording device; Rule 17 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule18(ClassificationRule):
    """Rule 18 - devices utilising non-viable human or animal tissue/cells.

    "All devices manufactured utilising tissues or cells of human or
    animal origin, or their derivatives, which are non-viable or rendered
    non-viable, are classified as class III, unless such devices are
    manufactured utilising tissues or cells of animal origin, or their
    derivatives, which are non-viable or rendered non-viable and are
    devices intended to come into contact with intact skin only."
    (Annex VIII, 7.5)

    Phase 1 (working from EUR-Lex text alone) flagged the carve-out as an
    unresolved regulatory gap: the rule text says it doesn't apply, but
    doesn't say what class then applies. Verified against MDCG 2021-24
    Rev.1, "Guidance on classification of medical devices" (pages 53-54;
    see docs/legal_sources/mdcg_2021-24_rule_18_tissue_devices.txt and
    docs/CLARIFICATIONS_RULE_18.md), that assumption was WRONG - MDCG's
    Note 3 resolves it explicitly:

    "This rule does not apply to devices manufactured utilizing tissues or
    cells of animal origin or their derivatives coming into contact with
    intact skin only. In such cases they are in class I in accordance to
    Rule 1. Intact skin includes the skin around an established stoma
    unless the skin is breached."

    The `ambiguous` flag has been removed accordingly - this is now a
    resolved, cited outcome (Class I), not a judgement call. The real
    example MDCG gives for it: "Leather components of orthopaedic
    appliances."
    """

    rule_id = "Rule 18"
    source_citation = f"{_SOURCE_BASE}, Section 7.5"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        base_gate = device.contains_human_or_animal_tissue_or_cells
        carve_out = (
            base_gate
            and device.tissue_origin == TissueOrigin.ANIMAL
            and device.tissue_contacts_intact_skin_only
        )
        escalates_to_iii = base_gate and not carve_out

        if escalates_to_iii:
            device_class = DeviceClass.III
        elif carve_out:
            device_class = DeviceClass.I
        else:
            device_class = None

        return RuleOutcome(
            rule_id=self.rule_id,
            applies=base_gate,
            device_class=device_class,
            rationale=(
                "Device is manufactured utilising non-viable tissues/cells of "
                "human or animal origin."
                if escalates_to_iii
                else (
                    "Animal-origin tissue/cells contacting intact skin only: "
                    "per MDCG 2021-24 Note 3, this falls outside Rule 18's "
                    "escalation and is Class I in accordance with Rule 1."
                    if carve_out
                    else "Device does not use human/animal tissue or cells; Rule 18 does not apply."
                )
            ),
            source_citation=self.source_citation,
        )


class Rule19(ClassificationRule):
    """Rule 19 - devices incorporating or consisting of nanomaterial.

    "All devices incorporating or consisting of nanomaterial are
    classified as: - class III if they present a high or medium potential
    for internal exposure; - class IIb if they present a low potential
    for internal exposure; and - class IIa if they present a negligible
    potential for internal exposure." (Annex VIII, 7.6)
    """

    rule_id = "Rule 19"
    source_citation = f"{_SOURCE_BASE}, Section 7.6"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = device.contains_nanomaterial
        exposure = device.nanomaterial_internal_exposure_potential
        candidates: list[tuple[bool, DeviceClass]] = [
            (
                gate and exposure in (NanomaterialExposurePotential.HIGH, NanomaterialExposurePotential.MEDIUM),
                DeviceClass.III,
            ),
            (gate and exposure == NanomaterialExposurePotential.LOW, DeviceClass.IIB),
            (gate and exposure == NanomaterialExposurePotential.NEGLIGIBLE, DeviceClass.IIA),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                f"Device incorporates or consists of nanomaterial with "
                f"'{exposure.value}' potential for internal exposure."
                if gate
                else "Device does not incorporate or consist of nanomaterial; Rule 19 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule20(ClassificationRule):
    """Rule 20 - inhaled medicinal product administration via body orifice.

    "All invasive devices with respect to body orifices, other than
    surgically invasive devices, which are intended to administer
    medicinal products by inhalation are classified as class IIa, unless
    their mode of action has an essential impact on the efficacy and
    safety of the administered medicinal product or they are intended to
    treat life-threatening conditions, in which case they are classified
    as class IIb." (Annex VIII, 7.7)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    56-57 (docs/legal_sources/mdcg_2021-24_rule_20_examples.txt): IIa -
    inhalers for nicotine replacement therapy, oxygen delivery via nasal
    cannula (non-life-threatening use), inhalers/nebulisers with no
    essential impact on drug efficacy/safety; IIb - nebulisers (not
    pre-charged with a specific medicinal product) where failure to
    deliver correct dosage could be hazardous.
    """

    rule_id = "Rule 20"
    source_citation = f"{_SOURCE_BASE}, Section 7.7"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = (
            device.invasiveness == Invasiveness.INVASIVE_BODY_ORIFICE
            and device.administers_medicinal_product_by_inhalation
        )
        candidates: list[tuple[bool, DeviceClass]] = [
            (gate and not device.inhalation_essential_impact_or_life_threatening, DeviceClass.IIA),
            (gate and device.inhalation_essential_impact_or_life_threatening, DeviceClass.IIB),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Non-surgical body-orifice-invasive device administering "
                "medicinal products by inhalation."
                if gate
                else "Device does not administer medicinal products by inhalation via a body orifice; Rule 20 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule21(ClassificationRule):
    """Rule 21 - substances introduced via body orifice or applied to skin
    that are absorbed or locally dispersed.

    "Devices that are composed of substances or of combinations of
    substances that are intended to be introduced into the human body via
    a body orifice or applied to the skin and that are absorbed by or
    locally dispersed in the human body are classified as: - class III
    if they, or their products of metabolism, are systemically absorbed
    by the human body in order to achieve the intended purpose; - class
    III if they achieve their intended purpose in the stomach or lower
    gastrointestinal tract and they, or their products of metabolism, are
    systemically absorbed by the human body; - class IIa if they are
    applied to the skin or if they are applied in the nasal or oral
    cavity as far as the pharynx, and achieve their intended purpose on
    those cavities; and - class IIb in all other cases."
    (Annex VIII, 7.8)

    Real worked examples confirmed against MDCG 2021-24 Rev.1, pages
    57-58 (docs/legal_sources/mdcg_2021-24_rule_21_examples.txt): III -
    systemically-absorbed fat absorbers, Na/Mg alginate acting in the
    stomach/lower GI tract; IIa - saline nasal/throat sprays, oral cough
    treatments acting only as far as the pharynx; IIb (catch-all) -
    simethicone/activated-charcoal oral preparations, vaginal
    moisturising gels, eye drops for hydration, ear drops (per MDCG's
    Note 2, ear drops only reach the ear drum and act locally on skin,
    so they are IIa - NOT the IIb catch-all - unless the ear drum is
    perforated).
    """

    rule_id = "Rule 21"
    source_citation = f"{_SOURCE_BASE}, Section 7.8"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        gate = device.composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin
        local_action_only = (
            gate
            and device.applied_to_skin_or_nasal_oral_cavity_to_pharynx
            and not device.systemically_absorbed
        )
        candidates: list[tuple[bool, DeviceClass]] = [
            (gate and device.systemically_absorbed, DeviceClass.III),
            (
                gate and device.achieves_purpose_in_stomach_or_lower_gi_tract and device.systemically_absorbed,
                DeviceClass.III,
            ),
            (local_action_only, DeviceClass.IIA),
            (gate and not local_action_only and not device.systemically_absorbed, DeviceClass.IIB),
        ]
        result = _evaluate_candidates(candidates)
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=gate,
            device_class=result,
            rationale=(
                "Device composed of substances introduced via a body orifice "
                "or applied to skin, absorbed by or locally dispersed in the "
                "body."
                if gate
                else "Device is not a substance-based absorbed/dispersed device; Rule 21 does not apply."
            ),
            source_citation=self.source_citation,
        )


class Rule22(ClassificationRule):
    """Rule 22 - active therapeutic devices with an integrated diagnostic
    function (e.g. closed-loop systems).

    "Active therapeutic devices with an integrated or incorporated
    diagnostic function which significantly determines the patient
    management by the device, such as closed loop systems or automated
    external defibrillators, are classified as class III." (Annex VIII, 7.9)
    """

    rule_id = "Rule 22"
    source_citation = f"{_SOURCE_BASE}, Section 7.9"

    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        applies = device.is_active and device.is_active_therapeutic_with_integrated_diagnostic_function
        return RuleOutcome(
            rule_id=self.rule_id,
            applies=applies,
            device_class=DeviceClass.III if applies else None,
            rationale=(
                "Active therapeutic device with an integrated/incorporated "
                "diagnostic function that significantly determines patient "
                "management (e.g. closed-loop system, automated external "
                "defibrillator)."
                if applies
                else "Device is not an active therapeutic device with a significant integrated diagnostic function; Rule 22 does not apply."
            ),
            source_citation=self.source_citation,
        )


ALL_RULES: list[type[ClassificationRule]] = [
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
]
