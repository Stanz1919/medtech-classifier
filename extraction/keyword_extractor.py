"""Default extractor: keyword/regex matching over free text.

Per the project brief, this keyword-based approach is the DEFAULT and
lead extraction path - not a fallback for an LLM extractor. An
LLM-based extractor is an optional future upgrade that would implement
the same ``extraction.base.Extractor`` interface; the rules engine
downstream never needs to know which one produced its input.

## Keyword grounding

Wherever the regulation itself defines a term, this extractor's keyword
list is built from that definition's own vocabulary rather than
invented synonyms - e.g. Annex VIII 2.3 defines "reusable surgical
instrument" as one used for "cutting, drilling, sawing, scratching,
scraping, clamping, retracting, clipping or similar procedures," so
those exact verbs are signals for surgical invasiveness, not just nouns
like "scalpel." Every signal group below cites the specific Article/
Annex VIII provision it is grounded in. See
docs/legal_sources/annex_viii_classification_rules.txt and
docs/legal_sources/article_2_definitions_extract.txt for the verbatim
source text.

## Coverage

56 of the 65 non-metadata fields on ``rules_engine.models.DeviceAttributes``
are attempted (86%) - grounded, per-rule, in the exact provisions listed
below. Verify this figure yourself rather than trust the count: it was
produced by scanning this file for every ``apply_bool(...)`` call and
``device.<field> = ...`` assignment and diffing against
``dataclasses.fields(DeviceAttributes)``, not by hand-counting.

- **Chapter I definitions** (Article 2(4)-(8); Annex VIII 2.1-2.8):
  invasiveness, duration, is_implantable, is_active, active_type,
  is_software, contacts_heart_or_central_circulatory_system (full
  Annex VIII 2.6 vessel list, not just "heart"), contacts_central_nervous_system
  (including "meninges," easy to miss vs. brain/spinal cord)
- **Rule 2**: channels_or_stores_for_infusion_administration_or_introduction,
  storage_target
- **Rule 3**: modifies_biological_or_chemical_composition,
  modification_treatment_type,
  in_vitro_direct_contact_with_cells_tissues_organs_or_embryos
- **Rule 4**: contacts_injured_skin_or_mucous_membrane, wound_contact_purpose
- **Rule 5**: body_orifice_site, liable_to_be_absorbed_by_mucous_membrane
  (including the negated "not liable to be absorbed" case)
- **Rules 6-8**: supplies_ionising_radiation, undergoes_chemical_change_in_body,
  placed_in_teeth, is_joint_replacement,
  is_spinal_disc_replacement_or_contacts_spinal_column,
  is_breast_implant_or_surgical_mesh, is_active_implantable_or_accessory,
  has_biological_effect_or_wholly_mainly_absorbed, administers_medicinal_product
- **Rule 9**: administers_or_exchanges_energy, emits_ionising_radiation_therapeutic
- **Rule 10**: diagnostic_supplies_energy_absorbed_by_body,
  diagnostic_illuminates_patient_visible_spectrum_only,
  diagnostic_images_in_vivo_radiopharmaceutical_distribution,
  diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes,
  diagnostic_variation_could_cause_immediate_danger,
  emits_ionising_radiation_diagnostic_or_interventional
- **Rule 11** (software): decision-support/monitoring *function* detection -
  see "Software" below
- **Rule 12**: administers_or_removes_substances_to_from_body
- **Rule 14**: contains_ancillary_medicinal_substance
- **Rule 15**: is_contraceptive_or_sti_prevention
- **Rule 16**: disinfect_clean_target (all four values: contact lenses,
  other medical device, invasive-device end-point, physical-action-only
  carve-out)
- **Rule 17**: is_xray_diagnostic_image_recording_device
- **Rule 18**: contains_human_or_animal_tissue_or_cells, tissue_origin,
  tissue_contacts_intact_skin_only
- **Rule 19**: contains_nanomaterial (gate only - see NOT covered)
- **Rule 20**: administers_medicinal_product_by_inhalation,
  inhalation_essential_impact_or_life_threatening
- **Rule 21**: composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin,
  systemically_absorbed (including the negated "not systemically
  absorbed" case), achieves_purpose_in_stomach_or_lower_gi_tract,
  applied_to_skin_or_nasal_oral_cavity_to_pharynx
- **Rule 22**: is_active_therapeutic_with_integrated_diagnostic_function

**NOT covered** (left at DeviceAttributes defaults) - 9 fields, split into
two honest categories rather than one vague "not implemented":

1. **Relational fields that cannot be inferred from a single device's own
   description**, full stop - they describe a relationship to a *second*
   device this extractor has no knowledge of: drives_or_influences_device_class,
   connected_to_active_device_class,
   controls_monitors_or_influences_therapeutic_class_iib_device,
   controls_monitors_or_influences_active_implantable_device.
2. **Genuine judgement calls the regulation itself does not reduce to a
   checklist**, matching this project's established policy (see
   docs/CLARIFICATIONS_RULE_8.md, docs/CLARIFICATIONS_RULE_11.md) of not
   forcing false confidence: administration_potentially_hazardous (Rule 6),
   energy_exchange_potentially_hazardous (Rule 9),
   administration_or_removal_potentially_hazardous (Rule 12) - "potentially
   hazardous" is inherently a risk-assessment judgement, not a textual
   fact; nanomaterial_internal_exposure_potential (Rule 19) - the
   negligible/low/medium/high tiers come from a SCENIHR-style technical
   exposure assessment methodology, not simple keyword matching;
   is_ancillary_component (Rule 8) - MDCG's own Note 1 says there is no
   blanket rule for this.

## Software: function is detected, severity is asked about

An earlier version of this extractor set ``is_software`` but never
attempted decision-support or monitoring *function* detection at all,
which meant a heartbeat-arrhythmia-detection app and a pure appointment
diary produced the identical result (Class I) - not appropriately
conservative, just wrong. Fixed: decision-support and monitoring
*function* are now detected from text (keywords like "detects
abnormalities," "informs a physician," "diagnoses," "monitors...vital");
once function is detected, the device is never allowed to fall into
Rule 11's "all other software" bucket. Severity (which of Rule 11's
three tiers applies) is a separate question this extractor still will
not guess - per MDCG's own guidance that this is a clinical-judgement
call (docs/CLARIFICATIONS_RULE_11.md) - but rather than silently
defaulting somewhere, it sets the conservative floor the detected
function alone supports (Class IIa, via SoftwareDecisionImpact.OTHER_IMPACT
or the monitoring-without-danger-flag path) and adds a
``clarifying_question`` naming exactly what additional information would
resolve it and what each answer implies.

## Design principle

Every match is logged as a human-readable signal (see
``extraction.base.ExtractionResult.matched_signals``) so a user can see
exactly which words drove which conclusion - this is not a black box.
Fields with no matched signal are left at their dataclass default rather
than guessed, consistent with this project's policy (established in the
rules engine) of not forcing false confidence. Where a genuine judgement
call remains, ``ExtractionResult.clarifying_questions`` names the exact
question to resolve it rather than leaving a vague "verify this" note.

This is regex/keyword matching, not NLP - it will have real false
positives and negatives on real text. It is meant to be a fast, fully
auditable starting point a human reviews and corrects, not a black-box
oracle. See README.md's Phase 2 section for known limitations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from extraction.base import Extractor, ExtractionResult
from rules_engine.models import (
    ActiveDeviceType,
    BodyOrificeSite,
    DeviceAttributes,
    DisinfectCleanTarget,
    Duration,
    Invasiveness,
    ModificationTreatmentType,
    SoftwareDecisionImpact,
    StorageTarget,
    TissueOrigin,
    WoundContactPurpose,
)


@dataclass(frozen=True)
class _Signal:
    pattern: str  # regex, matched case-insensitively
    label: str  # human-readable description used in matched_signals output


def _first_match(text: str, signals: list[_Signal]) -> _Signal | None:
    """Return the first signal (in priority order) whose pattern matches."""
    for signal in signals:
        if re.search(signal.pattern, text, re.IGNORECASE):
            return signal
    return None


def _any_match(text: str, signals: list[_Signal]) -> _Signal | None:
    """Like _first_match, but semantically for boolean "does any of these
    fire" checks rather than a priority-ordered enum resolution. Same
    implementation - kept as a separate name for readability at call
    sites."""
    return _first_match(text, signals)


# =========================================================================
# Invasiveness (Article 2(6); Annex VIII 2.1, 2.2, 2.3)
# =========================================================================
# Body-orifice-specific signals are checked first because they are more
# specific than generic surgical-invasion words that can be misleading in
# isolation (e.g. a plain "catheter" is far more often surgically
# invasive in general text, but "urinary catheter" is a body-orifice
# device - so the specific phrase must win if present).
_ORIFICE_SIGNALS = [
    _Signal(r"\bcontact lens", "contact lens (eye counts as a body orifice per Annex VIII 2.1)"),
    _Signal(r"\bnasal spray", "nasal spray"),
    _Signal(r"\bear ?drops?\b", "ear drops"),
    _Signal(r"\beye ?drops?\b", "eye drops"),
    _Signal(r"\binhaler|\bnebuli[sz]er", "inhaler/nebuliser"),
    _Signal(r"\bsuppositor", "suppository"),
    _Signal(r"\bvaginal", "vaginal application"),
    _Signal(r"\burethral|\burinary catheter", "urethral/urinary catheter"),
    _Signal(r"\bnasogastric", "nasogastric tube"),
    _Signal(r"\bendotracheal", "endotracheal tube"),
    _Signal(r"\bnasal cavity|\binserted (?:into|in) the nose", "nasal cavity"),
    _Signal(r"\boral cavity|\binserted (?:into|in) the mouth", "oral cavity"),
    _Signal(r"\bear canal", "ear canal"),
    _Signal(r"\brectal(?:ly)?", "rectal application"),
    # Annex VIII 2.1: "'Body orifice' means any natural opening in the
    # body, as well as the external surface of the eyeball, or any
    # permanent artificial opening, such as a stoma."
    _Signal(r"\bstoma\b", "stoma (Annex VIII 2.1: 'permanent artificial opening, such as a stoma')"),
    _Signal(r"\bnatural opening\b", "natural opening (Annex VIII 2.1)"),
]
_SURGICAL_SIGNALS = [
    _Signal(r"\bimplant(?:ed|able)?\b", "implant(ed/able)"),
    _Signal(r"\bsurgically inserted|\bsurgical incision", "surgically inserted / surgical incision"),
    # Annex VIII 2.2: "'Surgically invasive device' means: (a) an invasive
    # device which penetrates inside the body through the surface of the
    # body...with the aid or in the context of a surgical operation; and
    # (b) a device which produces penetration other than through a body
    # orifice." / Article 2(6): "'invasive device' means any device
    # which...penetrates inside the body...through the surface of the
    # body."
    _Signal(r"\bpenetrat(?:e|es|ing|ion)\b", "penetrat(es/ing/ion) (Annex VIII 2.2 / Article 2(6) wording)"),
    _Signal(r"\bsurgical operation\b", "surgical operation (Annex VIII 2.2 wording)"),
    _Signal(r"\bsubcutaneous", "subcutaneous placement"),
    _Signal(r"\bneedle\b", "needle"),
    _Signal(r"\bscalpel", "scalpel"),
    _Signal(r"\bcannula", "cannula"),
    _Signal(r"\bstent\b", "stent"),
    _Signal(r"\bpacemaker", "pacemaker"),
    _Signal(r"\bprosthe(?:sis|tic)", "prosthesis/prosthetic"),
    _Signal(r"\bsyringe", "syringe"),
    _Signal(r"\bsurgically invasive", "explicitly 'surgically invasive'"),
    # Annex VIII 2.3: "'Reusable surgical instrument' means an instrument
    # intended for surgical use in cutting, drilling, sawing, scratching,
    # scraping, clamping, retracting, clipping or similar procedures..."
    # These verbs are the regulation's own vocabulary for surgical
    # invasiveness, independent of whether "reusable" is also mentioned.
    _Signal(r"\b(?:used |intended )?(?:for |to )?cut(?:s|ting)?\b.{0,25}(?:tissue|body|skin)", "cutting tissue/body/skin (Annex VIII 2.3 wording)"),
    _Signal(r"\bcutting\b", "cutting (Annex VIII 2.3 wording)"),
    _Signal(r"\bdrilling\b", "drilling (Annex VIII 2.3 wording)"),
    _Signal(r"\bsawing\b", "sawing (Annex VIII 2.3 wording)"),
    _Signal(r"\bscratching\b", "scratching (Annex VIII 2.3 wording)"),
    _Signal(r"\bscraping\b", "scraping (Annex VIII 2.3 wording)"),
    _Signal(r"\bclamping\b", "clamping (Annex VIII 2.3 wording)"),
    _Signal(r"\bretracting\b", "retracting (Annex VIII 2.3 wording)"),
    _Signal(r"\bclipping\b", "clipping (Annex VIII 2.3 wording)"),
    _Signal(r"\bcatheter\b", "catheter (generic - assumed surgically invasive; check for a more specific orifice if this is wrong)"),
]
_NON_INVASIVE_SIGNALS = [
    _Signal(r"\bnon-?invasive", "explicitly 'non-invasive'"),
    _Signal(r"\btopical(?:ly)?", "topical"),
    _Signal(r"\bwearable\b", "wearable"),
    _Signal(r"\bdressing\b", "dressing"),
    _Signal(r"\bbandage", "bandage"),
    _Signal(r"\bskin surface|\bworn on the skin|\bapplied to (?:the )?skin", "applied to / worn on the skin"),
]

# --- Rule 5 body-orifice site detail ---
# Rule 5 (Annex VIII 5.1): the oral cavity/ear canal/nasal cavity
# exemptions are pinned to exact anatomical phrasing ("oral cavity as far
# as the pharynx," "ear canal up to the ear drum," "nasal cavity"). An
# earlier version of this extractor detected these phrases well enough
# to classify invasiveness but never populated body_orifice_site itself
# - meaning Rule 5's exemptions could never actually fire from extracted
# text even when the description clearly named one of the three sites.
_ORIFICE_SITE_ORAL_SIGNALS = [
    _Signal(r"\boral cavity\b", "oral cavity (Rule 5 wording: 'oral cavity as far as the pharynx')"),
    _Signal(r"\bpharynx\b", "pharynx (Rule 5 wording)"),
]
_ORIFICE_SITE_EAR_SIGNALS = [
    _Signal(r"\bear canal\b", "ear canal (Rule 5 wording: 'ear canal up to the ear drum')"),
    _Signal(r"\bear ?drum\b|\btympanic membrane\b", "ear drum / tympanic membrane (Rule 5 wording)"),
]
_ORIFICE_SITE_NASAL_SIGNALS = [
    _Signal(r"\bnasal cavity\b", "nasal cavity (Rule 5 wording)"),
]
_LIABLE_TO_BE_ABSORBED_SIGNALS = [
    _Signal(r"\bliable to be absorbed\b", "liable to be absorbed by the mucous membrane (Rule 5 wording)"),
]
_NOT_LIABLE_TO_BE_ABSORBED_SIGNALS = [
    _Signal(r"\bnot liable to be absorbed\b", "explicitly 'not liable to be absorbed' (Rule 5 wording)"),
]

# =========================================================================
# Non-invasive rule detail (Rules 2-3)
# =========================================================================
# Rule 2 (Annex VIII 4.2): "channelling or storing blood, body liquids,
# cells or tissues, liquids or gases for the purpose of eventual
# infusion, administration or introduction into the body."
_CHANNELS_STORES_SIGNALS = [
    _Signal(r"\bblood bag", "blood bag (Rule 2 wording)"),
    _Signal(r"\bchannel(?:s|ling|ing)?\b.{0,50}(?:blood|body liquid|liquid|gas|infusion)", "channels blood/liquid/gas (Rule 2 wording)"),
    _Signal(r"\bstor(?:e|es|ing)\b.{0,50}(?:blood|body liquid|organ|tissue|cell|for infusion)", "stores blood/liquid/organ/tissue/cell (Rule 2 wording)"),
    _Signal(r"\beventual infusion\b", "eventual infusion (Rule 2 wording)"),
]
_STORAGE_BLOOD_BAG_SIGNALS = [_Signal(r"\bblood bag", "blood bag (Rule 2 wording)")]
_STORAGE_ORGAN_TISSUE_SIGNALS = [
    _Signal(r"\borgan(?:s)?\b", "organ(s) (Rule 2 wording)"),
    _Signal(r"\bbody cells and tissues\b|\bparts of organs\b", "body cells and tissues / parts of organs (Rule 2 wording)"),
]
_STORAGE_BLOOD_LIQUID_SIGNALS = [
    _Signal(r"\bblood\b", "blood (Rule 2 wording)"),
    _Signal(r"\bbody liquid(?:s)?\b", "body liquid(s) (Rule 2 wording)"),
]

# Rule 3 (Annex VIII 4.3): "modifying the biological or chemical
# composition of human tissues or cells, blood, other body liquids...";
# treatment types "filtration, centrifugation or exchanges of gas,
# heat"; and separately, substances "used in vitro in direct contact
# with human cells, tissues or organs...or...with human embryos."
_MODIFIES_COMPOSITION_SIGNALS = [
    _Signal(r"\bmodif(?:y|ies|ying)\b.{0,50}(?:biological|chemical) composition", "modifies biological/chemical composition (Rule 3 wording)"),
]
_MODIFICATION_FILTRATION_SIGNALS = [
    _Signal(r"\bfiltration\b", "filtration (Rule 3 wording)"),
    _Signal(r"\bcentrifugation\b", "centrifugation (Rule 3 wording)"),
    _Signal(r"\b(?:exchange(?:s)? of|exchanging) gas\b|\bgas exchange\b", "gas exchange (Rule 3 wording)"),
    _Signal(r"\bheat exchange\b", "heat exchange (Rule 3 wording)"),
]
_IN_VITRO_SIGNALS = [
    _Signal(r"\bin vitro\b", "in vitro (Rule 3 wording)"),
    _Signal(r"\bhuman embryos\b", "human embryos (Rule 3 wording)"),
]

# =========================================================================
# Duration (Annex VIII Chapter I, Section 1; Article 2(8) single-use device)
# =========================================================================
_TRANSIENT_SIGNALS = [
    _Signal(r"\btransient\b", "explicitly 'transient'"),
    _Signal(r"\bsingle[- ]use\b", "single-use"),
    _Signal(r"\bone[- ]time use\b", "one-time use"),
    _Signal(r"\bless than (?:an? )?(?:60 ?minutes|1 ?hour)", "less than 60 minutes / 1 hour"),
    _Signal(r"\bmomentary\b|\bbriefly\b", "momentary/briefly"),
    # Article 2(8): "'single-use device' means a device that is intended
    # to be used on one individual during a single procedure." A device
    # used during a single procedure is, in practice, almost always
    # transient or at most short-term for the purposes of that procedure.
    _Signal(r"\b(?:during|for) a single procedure\b", "used during a single procedure (Article 2(8) wording)"),
    _Signal(r"\bused on one individual\b", "used on one individual (Article 2(8) wording)"),
]
_LONG_TERM_SIGNALS = [
    _Signal(r"\blong[- ]term\b", "explicitly 'long-term'"),
    _Signal(r"\bpermanent(?:ly)?\b", "permanent(ly)"),
    _Signal(r"\bmore than 30 days", "more than 30 days"),
    _Signal(r"\bchronic\b", "chronic"),
    _Signal(r"\bindefinite(?:ly)?\b", "indefinite(ly)"),
    _Signal(r"\bfor life\b|\blifetime\b", "for life / lifetime"),
]
_SHORT_TERM_SIGNALS = [
    _Signal(r"\bshort[- ]term\b", "explicitly 'short-term'"),
    _Signal(r"\bup to 30 days", "up to 30 days"),
    _Signal(r"\bfor (?:several|a few) (?:days|weeks)", "for several days/weeks"),
]

# =========================================================================
# Active device / software (Article 2(4); Annex VIII 2.4, 2.5)
# =========================================================================
_IMPLANTABLE_SIGNALS = [
    _Signal(r"\bimplant(?:ed|able)?\b", "implant(ed/able)"),
    # Article 2(5): "'implantable device' means any device...intended: to
    # be totally introduced into the human body, or to replace an
    # epithelial surface or the surface of the eye, by clinical
    # intervention and which is intended to remain in place after the
    # procedure."
    _Signal(r"\btotally introduced\b", "totally introduced (Article 2(5) wording)"),
    _Signal(r"\bclinical intervention\b.{0,40}\bremain(?:s)? in place\b|\bremain(?:s)? in place\b.{0,40}\bclinical intervention\b", "clinical intervention + remains in place (Article 2(5) wording)"),
]
_ACTIVE_SIGNALS = [
    # Article 2(4): "'active device' means any device, the operation of
    # which depends on a source of energy other than that generated by
    # the human body...or by gravity." The literal phrase "active device"
    # (or "active therapeutic/diagnostic/implantable device") is common
    # in real descriptions and must be matched directly, not just
    # inferred from power-source vocabulary.
    _Signal(r"\bactive (?:therapeutic |diagnostic |implantable |monitoring )?device\b", "explicitly 'active device' (Article 2(4) wording)"),
    _Signal(r"\bbattery|\bbatteries\b", "battery-powered"),
    _Signal(r"\bpowered\b", "powered"),
    _Signal(r"\belectronic", "electronic"),
    _Signal(r"\belectric(?:al)?\b", "electric(al)"),
    _Signal(r"\brechargeable", "rechargeable"),
    _Signal(r"\benergy source", "energy source"),
    _Signal(r"\bmotor(?:ised|ized)?\b", "motor(ised)"),
    # Named Rule 12 device types are inherently active (a suction/
    # infusion/feeding pump or dialysis machine requires a power source
    # to function) even when a description doesn't separately say
    # "active," "powered," etc.
    _Signal(r"\binfusion pump\b|\bfeeding pump\b|\bsuction pump\b|\bdialysis\b", "named active device type (infusion/feeding/suction pump, dialysis)"),
]
_ACTIVE_THERAPEUTIC_SIGNALS = [
    # Annex VIII 2.4: "'Active therapeutic device' means any active
    # device...to support, modify, replace or restore biological
    # functions or structures with a view to treatment or alleviation of
    # an illness, injury or disability."
    _Signal(r"\btherap(?:y|eutic)", "therapy/therapeutic"),
    _Signal(r"\btreat(?:s|ment)?\b", "treat(s)/treatment"),
    _Signal(r"\balleviat", "alleviat(e/es/ion) (Annex VIII 2.4 wording)"),
    _Signal(r"\bstimulat", "stimulat(es/ion)"),
    _Signal(r"\bdeliver(?:s)? energy|\badminister(?:s)? energy", "delivers/administers energy"),
    _Signal(r"\binfusion pump", "infusion pump"),
    _Signal(r"\bdefibrillat", "defibrillat(es/or)"),
]
_ACTIVE_DIAGNOSTIC_SIGNALS = [
    # Annex VIII 2.5: "'Active device intended for diagnosis and
    # monitoring' means any active device...to supply information for
    # detecting, diagnosing, monitoring or treating physiological
    # conditions, states of health, illnesses or congenital deformities."
    _Signal(r"\bmonitor(?:s|ing)?\b", "monitor(s/ing)"),
    _Signal(r"\bdiagnos", "diagnos(e/is/tic)"),
    _Signal(r"\bmeasur", "measur(e/es/ing)"),
    _Signal(r"\bdetect(?:s|ion)?\b", "detect(s/ion)"),
    _Signal(r"\bsens(?:e|ing|or)\b", "sense/sensing/sensor"),
    _Signal(r"\bimag(?:e|es|ing|ed)\b|\bscanner\b", "image(s)/imaging/scanner"),
]
_SOFTWARE_SIGNALS = [
    _Signal(r"\bsoftware\b", "software"),
    _Signal(r"\bmobile app\b|\bapp\b", "app"),
    _Signal(r"\balgorithm", "algorithm"),
    _Signal(r"\bapplication\b", "application"),
]

# --- Software decision-support / monitoring FUNCTION (distinct from severity) ---
_SOFTWARE_DECISION_SUPPORT_SIGNALS = [
    _Signal(r"\bdiagnos", "diagnos(e/es/is/tic)"),
    _Signal(r"\bdetects? abnormalit", "detects abnormalities"),
    _Signal(r"\binform(?:s)? a (?:physician|clinician|doctor|healthcare)", "informs a physician/clinician"),
    _Signal(r"\balert(?:s)?\b", "alert(s)"),
    _Signal(r"\brecommend(?:s)?\b.{0,25}(?:treatment|therapy|dose|dosage)", "recommends treatment/therapy/dose"),
    _Signal(r"\bsuggest(?:s)?\b.{0,25}(?:treatment|therapy)", "suggests treatment/therapy"),
    _Signal(r"\bflag(?:s)?\b.{0,25}abnormalit", "flags abnormalities"),
    _Signal(r"\banaly(?:s|z)e[sd]?\b.{0,30}(?:diagnos|treatment|decision)", "analyses ... to inform diagnosis/treatment/decision"),
    _Signal(r"\brank(?:s)?\b.{0,25}(?:treatment|therapy|option)", "ranks treatment options"),
]
_SOFTWARE_SEVERITY_DEATH_SIGNALS = [
    _Signal(r"\blife-?threatening\b", "life-threatening"),
    _Signal(r"\bfatal\b|\bdeath\b", "fatal/death"),
    _Signal(r"\birreversible\b", "irreversible"),
    _Signal(r"\bstroke\b", "stroke"),
    _Signal(r"\bcardiac arrest\b", "cardiac arrest"),
]
_SOFTWARE_SEVERITY_SERIOUS_SIGNALS = [
    _Signal(r"\bserious deterioration\b", "serious deterioration"),
    _Signal(r"\bsurgical intervention\b", "surgical intervention"),
    _Signal(r"\bhospitali[sz]ation\b", "hospitalisation"),
    _Signal(r"\burgent treatment\b", "urgent treatment"),
]
_SOFTWARE_MONITORING_SIGNALS = [
    _Signal(r"\bmonitor(?:s|ing)?\b.{0,25}(?:physiological|patient|vital)", "monitors physiological/patient/vital [processes]"),
    _Signal(r"\bcontinuous(?:ly)?\b.{0,20}(?:monitor|surveillance)", "continuous monitoring/surveillance"),
    _Signal(r"\btracks?\b.{0,20}(?:vital|physiological|heart ?rate|heartbeat)", "tracks vital/physiological signals"),
]
_SOFTWARE_VITAL_DANGER_SIGNALS = [
    _Signal(r"\bintensive care\b|\bicu\b", "intensive care / ICU"),
    _Signal(r"\bemergency care\b", "emergency care"),
    _Signal(r"\banaesthesia\b|\banesthesia\b", "anaesthesia"),
    _Signal(r"\bcritical care\b", "critical care"),
    _Signal(r"\blife-?threatening\b", "life-threatening"),
]

# =========================================================================
# Class I sub-qualifiers (Article 52(7))
# =========================================================================
_STERILE_SIGNALS = [_Signal(r"\bsterile\b|\bsterili[sz]ed\b", "sterile/sterilised")]
_MEASURING_SIGNALS = [_Signal(r"\bmeasur", "measur(e/es/ing/ement)")]
_REUSABLE_INSTRUMENT_SIGNALS = [
    _Signal(r"\breusable\b.{0,40}\b(?:instrument|scissors|forceps|clamp|retractor|surgical)", "reusable + surgical-instrument context"),
    _Signal(r"\b(?:instrument|scissors|forceps|clamp|retractor|surgical)\b.{0,40}\breusable\b", "surgical-instrument context + reusable"),
]

# =========================================================================
# Critical anatomy contact (Rules 6-8)
# =========================================================================
# Annex VIII 2.6: "'Central circulatory system' means the following
# blood vessels: arteriae pulmonales, aorta ascendens, arcus aortae,
# aorta descendens to the bifurcatio aortae, arteriae coronariae, arteria
# carotis communis, arteria carotis externa, arteria carotis interna,
# arteriae cerebrales, truncus brachiocephalicus, venae cordis, venae
# pulmonales, vena cava superior and vena cava inferior." This is an
# exhaustive, closed list, not "any blood vessel near the heart" - it is
# also the exact boundary between Class IIb and Class III in Rules 6-8,
# so both the Latin terms a clinical/technical description might use and
# their common English equivalents are matched.
_HEART_CIRC_SIGNALS = [
    _Signal(r"\bheart\b|\bcardiac\b", "heart/cardiac (direct contact context, not the specific vessel list)"),
    _Signal(r"\barteriae pulmonales\b|\bpulmonary arter(?:y|ies)\b", "pulmonary artery/arteries (Annex VIII 2.6: arteriae pulmonales)"),
    _Signal(r"\baorta ascendens\b|\bascending aorta\b", "ascending aorta (Annex VIII 2.6: aorta ascendens)"),
    _Signal(r"\barcus aortae\b|\baortic arch\b", "aortic arch (Annex VIII 2.6: arcus aortae)"),
    _Signal(r"\baorta descendens\b|\bdescending aorta\b", "descending aorta (Annex VIII 2.6: aorta descendens)"),
    _Signal(r"\bbifurcatio aortae\b|\baortic bifurcation\b", "aortic bifurcation (Annex VIII 2.6: bifurcatio aortae)"),
    _Signal(r"\baorta\b", "aorta (generic - Annex VIII 2.6 covers the aorta from aorta ascendens to the bifurcatio aortae)"),
    _Signal(r"\barteriae coronariae\b|\bcoronary arter(?:y|ies)\b|\bcoronary\b", "coronary artery/arteries (Annex VIII 2.6: arteriae coronariae)"),
    _Signal(r"\barteria carotis communis\b|\bcommon carotid\b|\bcca\b", "common carotid artery (Annex VIII 2.6: arteria carotis communis)"),
    _Signal(r"\barteria carotis externa\b|\bexternal carotid\b|\beca\b", "external carotid artery (Annex VIII 2.6: arteria carotis externa)"),
    _Signal(r"\barteria carotis interna\b|\binternal carotid\b|\bica\b", "internal carotid artery (Annex VIII 2.6: arteria carotis interna)"),
    _Signal(r"\bcarotid arter(?:y|ies)\b|\bcarotid\b", "carotid artery (generic - Annex VIII 2.6 covers the common/external/internal carotid arteries)"),
    # "MCA" (middle cerebral artery) gets its own signal because it shares
    # no substring with "cerebral artery" the way "anterior/posterior
    # cerebral artery" do (those already match the line below). Deliberately
    # NOT adding bare "ACA"/"PCA": the spelled-out forms are already covered
    # via substring, and PCA specifically collides with "Patient-Controlled
    # Analgesia" - a genuinely common phrase in infusion-pump device text,
    # so a bare abbreviation there would be a real false-positive risk, not
    # a hypothetical one.
    _Signal(r"\bmca\b|\bmiddle cerebral artery\b", "middle cerebral artery / MCA (Annex VIII 2.6: arteriae cerebrales)"),
    _Signal(r"\barteriae cerebrales\b|\bcerebral arter(?:y|ies)\b", "cerebral artery/arteries (Annex VIII 2.6: arteriae cerebrales)"),
    _Signal(r"\bcerebrovascular\b", "cerebrovascular (generic - implies a cerebral-artery/circulatory context per Annex VIII 2.6, not itself the defined term - verify it isn't describing brain tissue instead, see the CNS signals below)"),
    _Signal(r"\btruncus brachiocephalicus\b|\bbrachiocephalic trunk\b", "brachiocephalic trunk (Annex VIII 2.6: truncus brachiocephalicus)"),
    _Signal(r"\bvenae cordis\b|\bcardiac vein(?:s)?\b", "cardiac vein(s) (Annex VIII 2.6: venae cordis)"),
    _Signal(r"\bvenae pulmonales\b|\bpulmonary vein(?:s)?\b", "pulmonary vein(s) (Annex VIII 2.6: venae pulmonales)"),
    _Signal(r"\bvena cava superior\b|\bsuperior vena cava\b", "superior vena cava (Annex VIII 2.6: vena cava superior)"),
    _Signal(r"\bvena cava inferior\b|\binferior vena cava\b", "inferior vena cava (Annex VIII 2.6: vena cava inferior)"),
    _Signal(r"\bvena cava\b", "vena cava (generic - Annex VIII 2.6 covers both superior and inferior)"),
    _Signal(r"\bcirculatory system\b", "circulatory system (generic phrase, not itself Annex VIII 2.6's defined term - verify it means the CENTRAL circulatory system, not peripheral vasculature)"),
]
# Annex VIII 2.7: "'Central nervous system' means the brain, meninges and
# spinal cord." Only three anatomical structures - note "meninges" is
# easy to miss if grounding from common sense rather than the definition
# itself.
_CNS_SIGNALS = [
    # Negative lookahead on "cerebral" excludes "cerebral artery/arteries/
    # vascular/vein(s)" - those describe a blood vessel (central
    # CIRCULATORY system, 2.6, see _HEART_CIRC_SIGNALS above), not brain
    # TISSUE (central nervous system, 2.7). A stent sitting inside a
    # cerebral artery contacts the vessel wall, not the brain itself -
    # conflating the two would misreport which Rule 8 exception actually
    # applies, even though both happen to escalate to the same Class III
    # today. "cerebral cortex/hemisphere/edema" etc. still match correctly.
    _Signal(r"\bbrain\b|\bcerebral\b(?!\s+(?:artery|arteries|vascular|vein|veins))", "brain/cerebral (Annex VIII 2.7: 'the brain')"),
    _Signal(r"\bmeninges\b|\bmeningeal\b", "meninges (Annex VIII 2.7 - easily missed vs. brain/spinal cord)"),
    _Signal(r"\bspinal cord\b", "spinal cord (Annex VIII 2.7: 'the...spinal cord')"),
    _Signal(r"\bcentral nervous system\b|\bcns\b", "explicitly 'central nervous system' / CNS"),
]
_PLACED_IN_TEETH_SIGNALS = [
    # Deliberately narrower than "dental implant" - see MDCG 2021-24 Note 4
    # (docs/CLARIFICATIONS_RULE_8.md): jawbone-anchored implants are IIb,
    # NOT the "placed in the teeth" IIa exception. Only genuine intra-tooth
    # restorations should match here.
    _Signal(r"\bdental filling", "dental filling"),
    _Signal(r"\btooth crown\b|\bdental crown\b", "tooth/dental crown"),
    _Signal(r"\bdental bridge\b", "dental bridge"),
    _Signal(r"\bdental (?:alloy|ceramic|polymer)", "dental alloy/ceramic/polymer"),
]
_JOINT_REPLACEMENT_SIGNALS = [
    _Signal(r"\b(?:hip|knee|shoulder|ankle) replacement", "named joint replacement"),
    _Signal(r"\btotal (?:hip|knee) (?:arthroplasty|replacement)", "total joint arthroplasty/replacement"),
    _Signal(r"\bjoint replacement", "joint replacement"),
]
_SPINAL_SIGNALS = [
    _Signal(r"\bspinal disc\b", "spinal disc"),
    _Signal(r"\bspinal column\b|\bvertebra", "spinal column/vertebra"),
    _Signal(r"\bpedicle screw", "pedicle screw"),
    _Signal(r"\binterbody fusion", "interbody fusion"),
]
_BREAST_MESH_SIGNALS = [
    _Signal(r"\bbreast implant", "breast implant"),
    _Signal(r"\bbreast tissue expander", "breast tissue expander"),
    _Signal(r"\bsurgical mesh\b|\bhernia mesh\b", "surgical/hernia mesh"),
]
_ACTIVE_IMPLANTABLE_SIGNALS = [
    _Signal(r"\bpacemaker", "pacemaker"),
    # Requires an "implantable" or "cardioverter" qualifier, NOT bare
    # "defibrillator" - an automated EXTERNAL defibrillator (AED) is
    # explicitly non-implantable (it belongs under Rule 22, not this
    # active-implantable-accessory signal) and would otherwise be a false
    # positive here.
    _Signal(r"\bimplantable (?:cardioverter )?defibrillator\b|\bcardioverter defibrillator\b|\bicd\b", "implantable cardioverter defibrillator"),
    _Signal(r"\bcochlear implant", "cochlear implant"),
    _Signal(r"\b(?:neuro|nerve) ?stimulator", "neuro/nerve stimulator"),
]

# =========================================================================
# Shared physical-effect vocabulary (Rules 6-10)
# =========================================================================
# Rules 6, 7, 9 and 10 all turn on whether a device "supplies/emits
# ionising radiation" - the regulation itself is inconsistent about
# spelling this across rules (Rule 6 uses "ionising," Rule 7/9/10 use
# "ionizing"), so both are matched.
_IONISING_RADIATION_SIGNALS = [
    _Signal(r"\bionising radiation\b|\bionizing radiation\b", "ionising/ionizing radiation (Rules 6/7/9/10 wording)"),
]
# Rules 7 and 8: "undergo chemical change in the body."
_CHEMICAL_CHANGE_SIGNALS = [
    _Signal(r"\bundergo(?:es)? chemical change\b|\bchemical change in the body\b", "undergoes chemical change in the body (Rules 7/8 wording)"),
]

# --- Rule 9: active therapeutic devices administering/exchanging energy ---
_ADMINISTERS_EXCHANGES_ENERGY_SIGNALS = [
    _Signal(r"\badminister(?:s)? or exchange(?:s)? energy\b", "administer or exchange energy (Rule 9 wording)"),
    _Signal(r"\bexchange(?:s)? energy\b", "exchanges energy (Rule 9 wording)"),
    _Signal(r"\badminister(?:s)? energy\b", "administers energy (Rule 9 wording)"),
]
# Rule 9's fourth paragraph: "All active devices intended to emit
# ionizing radiation for therapeutic purposes...are classified as class
# IIb." Distinct from Rule 10's diagnostic/interventional radiology
# signal - same underlying "ionising radiation" vocabulary, different
# purpose (therapeutic vs. diagnostic).
_IONISING_RADIATION_THERAPEUTIC_SIGNALS = [
    _Signal(r"\bionising radiation\b.{0,30}therapeutic\b|\bionizing radiation\b.{0,30}therapeutic\b", "ionising radiation for therapeutic purposes (Rule 9 wording)"),
    _Signal(r"\bradiotherapy\b", "radiotherapy"),
    _Signal(r"\btherapeutic radiology\b", "therapeutic radiology (Rule 9/10 wording)"),
]

# --- Rule 10: active devices for diagnosis and monitoring ---
_DIAGNOSTIC_ENERGY_ABSORBED_SIGNALS = [
    _Signal(r"\bsupply(?:ies)? energy\b.{0,40}absorbed by the human body\b", "supplies energy absorbed by the human body (Rule 10 wording)"),
    _Signal(r"\benergy\b.{0,20}absorbed by the (?:human )?body\b", "energy absorbed by the body (Rule 10 wording)"),
]
_DIAGNOSTIC_ILLUMINATE_SIGNALS = [
    _Signal(r"\billuminat(?:e|es|ion)\b.{0,30}visible spectrum\b", "illuminate...visible spectrum (Rule 10 wording)"),
    _Signal(r"\bvisible spectrum\b", "visible spectrum (Rule 10 wording)"),
]
_RADIOPHARMACEUTICAL_SIGNALS = [
    _Signal(r"\bradiopharmaceutical", "radiopharmaceutical(s) (Rule 10 wording)"),
    _Signal(r"\bin vivo distribution\b", "in vivo distribution (Rule 10 wording)"),
]
_DIRECT_DIAGNOSIS_VITAL_SIGNALS = [
    _Signal(r"\bdirect diagnosis\b", "direct diagnosis (Rule 10 / Annex VIII 3.7 wording)"),
    _Signal(r"\bvital physiological process", "vital physiological process(es) (Rule 10 wording)"),
]
_IMMEDIATE_DANGER_SIGNALS = [
    _Signal(r"\bimmediate danger\b", "immediate danger (Rule 10 wording)"),
    # Rule 10's own named examples of vital parameters: "variations in
    # cardiac performance, respiration, activity of the central nervous
    # system."
    _Signal(r"\bcardiac performance\b", "cardiac performance (Rule 10 named example)"),
    _Signal(r"\brespiration\b", "respiration (Rule 10 named example)"),
]
_DIAGNOSTIC_THERAPEUTIC_RADIOLOGY_SIGNALS = [
    _Signal(r"\bdiagnostic radiology\b|\btherapeutic radiology\b", "diagnostic/therapeutic radiology (Rule 10 wording)"),
    _Signal(r"\binterventional radiology\b", "interventional radiology (Rule 10 wording)"),
    _Signal(r"\bct scan(?:ner)?\b|\bcomputed tomography\b", "CT scanner / computed tomography"),
    _Signal(r"\bfluoroscop", "fluoroscopy"),
]

# --- Rule 22: active therapeutic devices with integrated diagnostic function ---
_CLOSED_LOOP_AED_SIGNALS = [
    _Signal(r"\bclosed[- ]loop\b", "closed-loop system (Rule 22 named example)"),
    _Signal(r"\bautomated external defibrillator\b|\baed\b", "automated external defibrillator (Rule 22 named example)"),
    _Signal(r"\bintegrated diagnostic function\b|\bincorporated diagnostic function\b", "integrated/incorporated diagnostic function (Rule 22 wording)"),
]

# =========================================================================
# Physical effects / medicinal content
# =========================================================================
_ABSORBABLE_SIGNALS = [
    _Signal(r"\b(?:bio)?absorbable\b", "(bio)absorbable"),
    _Signal(r"\bresorbable\b", "resorbable"),
    _Signal(r"\bbiodegradable\b", "biodegradable"),
]
_ADMINISTERS_MEDICINAL_PRODUCT_SIGNALS = [
    _Signal(r"\bdrug[- ]elut", "drug-eluting"),
    _Signal(r"\bdrug delivery\b", "drug delivery"),
    _Signal(r"\breleases? medicat", "releases medication"),
    _Signal(r"\badminister(?:s|ing)? (?:a )?(?:medicinal|drug|medication)", "administers medicinal product"),
]
_ANCILLARY_MEDICINAL_SUBSTANCE_SIGNALS = [
    _Signal(r"\bantibiotic[- ]coat", "antibiotic-coated"),
    _Signal(r"\bcontain(?:s|ing)? (?:an )?antibiotic", "contains antibiotic"),
    _Signal(r"\bmedicated\b", "medicated"),
    _Signal(r"\bspermicide\b", "spermicide"),
    _Signal(r"\bheparin[- ]coat", "heparin-coated"),
    _Signal(r"\bdrug[- ]elut", "drug-eluting"),
]
_CONTRACEPTIVE_SIGNALS = [
    _Signal(r"\bcondom\b", "condom"),
    _Signal(r"\bcontracept", "contracept(ive/ion)"),
    _Signal(r"\bintrauterine device\b|\biud\b", "intrauterine device (IUD)"),
    _Signal(r"\bdiaphragm\b", "diaphragm"),
]
_XRAY_RECORDING_SIGNALS = [
    _Signal(r"\bx-?ray (?:image|detector|sensor|recording)", "X-ray image recording"),
    _Signal(r"\bradiograph", "radiograph"),
]
_NANOMATERIAL_SIGNALS = [
    _Signal(r"\bnanomaterial", "nanomaterial"),
    _Signal(r"\bnanoparticle", "nanoparticle"),
    _Signal(r"\bnano[- ]coat", "nano-coating"),
]
_TISSUE_ANIMAL_SIGNALS = [
    _Signal(r"\bporcine\b", "porcine"),
    _Signal(r"\bbovine\b", "bovine"),
    _Signal(r"\bxenograft", "xenograft"),
    _Signal(r"\banimal[- ](?:derived|origin|sourced)", "animal-derived/origin/sourced"),
    _Signal(r"\banimal tissue\b|\banimal cells?\b", "animal tissue/cells (Rule 18 wording)"),
]
_TISSUE_HUMAN_SIGNALS = [
    _Signal(r"\ballograft", "allograft"),
    _Signal(r"\bhuman[- ](?:derived|origin|donor|cadaveric)", "human-derived/origin/donor/cadaveric"),
    _Signal(r"\bcadaveric\b", "cadaveric"),
    _Signal(r"\bhuman tissue\b", "human tissue"),
]
_INHALATION_SIGNALS = [
    _Signal(r"\binhaler\b", "inhaler"),
    _Signal(r"\bnebuli[sz]er\b", "nebuliser"),
    _Signal(r"\binhalation\b", "inhalation"),
]
# Rule 20: "unless their mode of action has an essential impact on the
# efficacy and safety of the administered medicinal product or they are
# intended to treat life-threatening conditions."
_INHALATION_LIFE_THREATENING_SIGNALS = [
    _Signal(r"\blife-?threatening condition", "life-threatening condition(s) (Rule 20 wording)"),
    _Signal(r"\bessential impact\b.{0,30}efficacy and safety\b", "essential impact on efficacy and safety (Rule 20 wording)"),
]

# --- Rule 12: active devices administering/removing substances ---
_ADMINISTERS_OR_REMOVES_SUBSTANCES_SIGNALS = [
    # Deliberately permissive middle gap (up to 20 chars of "and", "or",
    # "and/or", punctuation, etc.) rather than requiring the regulation's
    # exact "and/or" - real descriptions paraphrase this connector freely.
    _Signal(r"\badminister(?:s)?\b.{0,20}remove(?:s)?\b", "administers...removes (Rule 12 wording)"),
    _Signal(r"\bremove(?:s)?\b.{0,40}(?:from the body|from the patient)", "removes...from the body (Rule 12 wording)"),
    _Signal(r"\binfusion pump\b|\bfeeding pump\b|\bsuction pump\b|\bdialysis\b", "named Rule 12 device type (infusion/feeding/suction pump, dialysis)"),
]

# --- Rule 16: disinfecting/cleaning/rinsing/hydrating/sterilising devices ---
_DISINFECT_CONTACT_LENS_SIGNALS = [
    _Signal(r"\bcontact lens.{0,30}(?:disinfect|clean|rins|hydrat)", "disinfecting/cleaning/rinsing/hydrating contact lenses (Rule 16 wording)"),
    _Signal(r"(?:disinfect|clean|rins|hydrat)\w*\b.{0,30}contact lens", "disinfecting/cleaning contact lenses (Rule 16 wording)"),
    _Signal(r"\bcontact lens (?:solution|storing solution|cleaner)\b", "contact lens solution/cleaner"),
]
_DISINFECT_INVASIVE_ENDPOINT_SIGNALS = [
    _Signal(r"\bwasher-disinfector\b.{0,40}(?:invasive|endoscop)", "washer-disinfector for invasive devices/endoscopes (Rule 16 wording)"),
    _Signal(r"\bend point of processing\b", "end point of processing (Rule 16 wording)"),
    _Signal(r"\bdisinfecting solution\b.{0,40}invasive", "disinfecting solution for invasive devices"),
]
_DISINFECT_OTHER_DEVICE_SIGNALS = [
    _Signal(r"\bdisinfect(?:ing|s)?\b.{0,30}medical device", "disinfecting medical devices (Rule 16 wording)"),
    _Signal(r"\bsterilis(?:e|ing|ation)\b.{0,30}medical device|\bsterilizing\b.{0,30}medical device", "sterilising medical devices (Rule 16 wording)"),
]
_PHYSICAL_ACTION_ONLY_SIGNALS = [
    _Signal(r"\bphysical action only\b", "physical action only (Rule 16 carve-out wording)"),
    _Signal(r"\bmechanical (?:action|cleaning) only\b", "mechanical action/cleaning only (Rule 16 carve-out wording)"),
]

# --- Rule 18: the "intact skin only" carve-out ---
_INTACT_SKIN_ONLY_SIGNALS = [
    _Signal(r"\bintact skin only\b", "intact skin only (Rule 18 carve-out wording)"),
    _Signal(r"\bcontact with intact skin\b", "contact with intact skin (Rule 18 wording)"),
]

# --- Rule 21: substance-based devices absorbed/dispersed via orifice or skin ---
_SUBSTANCE_ABSORBED_DISPERSED_SIGNALS = [
    _Signal(r"\bcomposed of substances\b", "composed of substances (Rule 21 wording)"),
    _Signal(r"\blocally dispersed\b", "locally dispersed (Rule 21 wording)"),
    _Signal(r"\babsorbed by (?:the )?human body\b", "absorbed by the human body (Rule 21 wording)"),
]
_SYSTEMICALLY_ABSORBED_SIGNALS = [
    # Deliberately excludes a preceding "not"/"no"/"non-" via negative
    # lookbehind - "not systemically absorbed" must NOT match this
    # positive signal (see _NOT_SYSTEMICALLY_ABSORBED_SIGNALS below for
    # the explicit negative case, same pattern as Rule 5's
    # liable/not-liable-to-be-absorbed handling).
    _Signal(r"(?<!not )(?<!non-)(?<!non )\bsystemically absorbed\b|\bsystemic absorption\b", "systemically absorbed (Rule 21 wording)"),
]
_NOT_SYSTEMICALLY_ABSORBED_SIGNALS = [
    _Signal(r"\bnot systemically absorbed\b|\bnon-systemically absorbed\b", "explicitly 'not systemically absorbed' (Rule 21 wording)"),
]
_STOMACH_LOWER_GI_SIGNALS = [
    _Signal(r"\bstomach\b", "stomach (Rule 21 wording)"),
    _Signal(r"\blower gastrointestinal tract\b|\blower gi tract\b", "lower gastrointestinal tract (Rule 21 wording)"),
]
_APPLIED_SKIN_NASAL_ORAL_PHARYNX_SIGNALS = [
    _Signal(r"\bapplied to the skin\b", "applied to the skin (Rule 21 wording)"),
    _Signal(r"\bnasal\b.{0,15}(?:cavity)?.{0,15}pharynx\b|\boral cavity\b.{0,15}pharynx\b", "nasal/oral cavity as far as the pharynx (Rule 21 wording)"),
]

# =========================================================================
# Wound contact (Rule 4)
# =========================================================================
_WOUND_CONTACT_GATE_SIGNALS = [
    _Signal(r"\bwound\b", "wound"),
    _Signal(r"\bulcer", "ulcer"),
    _Signal(r"\bburn\b", "burn"),
    _Signal(r"\bdressing\b", "dressing"),
    _Signal(r"\bincision site\b", "incision site"),
]
_WOUND_BREACHED_DERMIS_SIGNALS = [
    _Signal(r"\bbreached dermis\b", "breached dermis"),
    _Signal(r"\bfull[- ]thickness\b", "full-thickness"),
    _Signal(r"\bsevere (?:wound|burn|ulcer)", "severe wound/burn/ulcer"),
    _Signal(r"\bsecondary intent\b", "secondary intent healing"),
    _Signal(r"\bdeep wound\b", "deep wound"),
]
_WOUND_MICROENVIRONMENT_SIGNALS = [
    _Signal(r"\bmicro-?environment\b", "micro-environment"),
    _Signal(r"\bmoist wound\b", "moist wound healing"),
    _Signal(r"\bhydrogel\b", "hydrogel"),
    _Signal(r"\bhydrocolloid\b", "hydrocolloid"),
]
_WOUND_BARRIER_SIGNALS = [
    _Signal(r"\babsorb(?:s|ent|ing)? exudate", "absorbs exudate"),
    _Signal(r"\bmechanical barrier\b", "mechanical barrier"),
    _Signal(r"\bcompression\b", "compression"),
    _Signal(r"\bgauze\b", "gauze"),
    _Signal(r"\badhesive bandage\b|\bsticking plaster\b", "adhesive bandage / sticking plaster"),
]


class KeywordExtractor(Extractor):
    """Default rule-based extractor. See module docstring for coverage."""

    def extract(self, text: str) -> ExtractionResult:
        device = DeviceAttributes(description=text)
        signals: list[str] = []
        notes: list[str] = []
        questions: list[str] = []

        def apply_bool(field_name: str, matches: list[_Signal]) -> bool:
            hit = _any_match(text, matches)
            if hit:
                setattr(device, field_name, True)
                signals.append(f"{field_name} = True (matched: {hit.label})")
                return True
            return False

        # --- Invasiveness ---
        orifice_hit = _first_match(text, _ORIFICE_SIGNALS)
        surgical_hit = _first_match(text, _SURGICAL_SIGNALS)
        non_invasive_hit = _first_match(text, _NON_INVASIVE_SIGNALS)
        if orifice_hit:
            device.invasiveness = Invasiveness.INVASIVE_BODY_ORIFICE
            signals.append(f"invasiveness = INVASIVE_BODY_ORIFICE (matched: {orifice_hit.label})")
        elif surgical_hit:
            device.invasiveness = Invasiveness.SURGICALLY_INVASIVE
            signals.append(f"invasiveness = SURGICALLY_INVASIVE (matched: {surgical_hit.label})")
        elif non_invasive_hit:
            device.invasiveness = Invasiveness.NON_INVASIVE
            signals.append(f"invasiveness = NON_INVASIVE (matched: {non_invasive_hit.label})")
        else:
            notes.append(
                "invasiveness: no signal found, left at default NON_INVASIVE - verify this is correct."
            )

        # --- Rule 5 body-orifice site detail (only meaningful when
        # invasive_body_orifice, but harmless to compute regardless -
        # Rule 5 itself gates on invasiveness) ---
        if device.invasiveness == Invasiveness.INVASIVE_BODY_ORIFICE:
            oral_hit = _any_match(text, _ORIFICE_SITE_ORAL_SIGNALS)
            ear_hit = _any_match(text, _ORIFICE_SITE_EAR_SIGNALS)
            nasal_hit = _any_match(text, _ORIFICE_SITE_NASAL_SIGNALS)
            if oral_hit:
                device.body_orifice_site = BodyOrificeSite.ORAL_CAVITY_TO_PHARYNX
                signals.append(f"body_orifice_site = ORAL_CAVITY_TO_PHARYNX (matched: {oral_hit.label})")
            elif ear_hit:
                device.body_orifice_site = BodyOrificeSite.EAR_CANAL_TO_EARDRUM
                signals.append(f"body_orifice_site = EAR_CANAL_TO_EARDRUM (matched: {ear_hit.label})")
            elif nasal_hit:
                device.body_orifice_site = BodyOrificeSite.NASAL_CAVITY
                signals.append(f"body_orifice_site = NASAL_CAVITY (matched: {nasal_hit.label})")
            else:
                device.body_orifice_site = BodyOrificeSite.OTHER_ORIFICE
                notes.append(
                    "body_orifice_site: device is body-orifice-invasive but no oral/ear/nasal "
                    "site matched - defaulted to OTHER_ORIFICE, meaning Rule 5's short/long-term "
                    "exemptions for those three specific sites will not apply. Verify this is "
                    "correct if the description does describe one of those sites."
                )

            not_absorbed_hit = _any_match(text, _NOT_LIABLE_TO_BE_ABSORBED_SIGNALS)
            absorbed_hit = _any_match(text, _LIABLE_TO_BE_ABSORBED_SIGNALS)
            if not_absorbed_hit:
                device.liable_to_be_absorbed_by_mucous_membrane = False
                signals.append(f"liable_to_be_absorbed_by_mucous_membrane = False (matched: {not_absorbed_hit.label})")
            elif absorbed_hit:
                device.liable_to_be_absorbed_by_mucous_membrane = True
                signals.append(f"liable_to_be_absorbed_by_mucous_membrane = True (matched: {absorbed_hit.label})")

        # --- Duration ---
        transient_hit = _first_match(text, _TRANSIENT_SIGNALS)
        long_term_hit = _first_match(text, _LONG_TERM_SIGNALS)
        short_term_hit = _first_match(text, _SHORT_TERM_SIGNALS)
        if transient_hit:
            device.duration = Duration.TRANSIENT
            signals.append(f"duration = TRANSIENT (matched: {transient_hit.label})")
        elif long_term_hit:
            device.duration = Duration.LONG_TERM
            signals.append(f"duration = LONG_TERM (matched: {long_term_hit.label})")
        elif short_term_hit:
            device.duration = Duration.SHORT_TERM
            signals.append(f"duration = SHORT_TERM (matched: {short_term_hit.label})")
        else:
            notes.append(
                "duration: no signal found, left at default NOT_APPLICABLE - several rules "
                "(5-8) depend on this and will not fire without it."
            )

        # --- Rule 2: non-invasive channelling/storing devices ---
        channels_stores_hit = _any_match(text, _CHANNELS_STORES_SIGNALS)
        if channels_stores_hit:
            device.channels_or_stores_for_infusion_administration_or_introduction = True
            signals.append(
                f"channels_or_stores_for_infusion_administration_or_introduction = True "
                f"(matched: {channels_stores_hit.label})"
            )
            blood_bag_hit = _any_match(text, _STORAGE_BLOOD_BAG_SIGNALS)
            organ_tissue_hit = _any_match(text, _STORAGE_ORGAN_TISSUE_SIGNALS)
            blood_liquid_hit = _any_match(text, _STORAGE_BLOOD_LIQUID_SIGNALS)
            if blood_bag_hit:
                device.storage_target = StorageTarget.BLOOD_BAGS
                signals.append(f"storage_target = BLOOD_BAGS (matched: {blood_bag_hit.label})")
            elif organ_tissue_hit:
                device.storage_target = StorageTarget.ORGANS_CELLS_TISSUES
                signals.append(f"storage_target = ORGANS_CELLS_TISSUES (matched: {organ_tissue_hit.label})")
            elif blood_liquid_hit:
                device.storage_target = StorageTarget.BLOOD_OR_OTHER_BODY_LIQUIDS
                signals.append(f"storage_target = BLOOD_OR_OTHER_BODY_LIQUIDS (matched: {blood_liquid_hit.label})")
            else:
                device.storage_target = StorageTarget.OTHER
                notes.append(
                    "storage_target: channelling/storing context found but no specific target "
                    "(blood/organs/blood bags) matched - defaulted to OTHER (Rule 2's Class I "
                    "catch-all, unless connected to a higher-class active device)."
                )

        # --- Rule 3: modifies biological/chemical composition; in vitro contact ---
        modifies_hit = _any_match(text, _MODIFIES_COMPOSITION_SIGNALS)
        if modifies_hit:
            device.modifies_biological_or_chemical_composition = True
            signals.append(f"modifies_biological_or_chemical_composition = True (matched: {modifies_hit.label})")
            filtration_hit = _any_match(text, _MODIFICATION_FILTRATION_SIGNALS)
            if filtration_hit:
                device.modification_treatment_type = ModificationTreatmentType.FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE
                signals.append(
                    f"modification_treatment_type = FILTRATION_CENTRIFUGATION_GAS_OR_HEAT_EXCHANGE "
                    f"(matched: {filtration_hit.label})"
                )
            else:
                device.modification_treatment_type = ModificationTreatmentType.OTHER
                notes.append(
                    "modification_treatment_type: composition-modifying context found but no "
                    "filtration/centrifugation/gas/heat-exchange signal matched - defaulted to "
                    "OTHER (Rule 3's Class IIb outcome, rather than the IIa exception)."
                )
        in_vitro_hit = _any_match(text, _IN_VITRO_SIGNALS)
        if in_vitro_hit:
            device.in_vitro_direct_contact_with_cells_tissues_organs_or_embryos = True
            signals.append(
                f"in_vitro_direct_contact_with_cells_tissues_organs_or_embryos = True "
                f"(matched: {in_vitro_hit.label})"
            )

        # --- Implantable / active / software ---
        apply_bool("is_implantable", _IMPLANTABLE_SIGNALS)

        # Annex VIII 2.4 and 2.5 both define their respective device types
        # as "any ACTIVE device used...to support/modify/replace/restore..."
        # (therapeutic) or "...to supply information for detecting,
        # diagnosing, monitoring..." (diagnostic) - i.e. the therapeutic/
        # diagnostic function vocabulary is ITSELF drawn from a definition
        # that presupposes active-device status. So a therapeutic or
        # diagnostic function match is sufficient evidence for is_active on
        # its own, not just a fallback classification once is_active is
        # already known some other way (e.g. "a CT scanner" or "monitors
        # vital signs" should set is_active even with no separate
        # battery/powered/"active device" phrase present).
        active_hit = _any_match(text, _ACTIVE_SIGNALS)
        therapeutic_hit = _any_match(text, _ACTIVE_THERAPEUTIC_SIGNALS)
        diagnostic_hit = _any_match(text, _ACTIVE_DIAGNOSTIC_SIGNALS)
        if active_hit or therapeutic_hit or diagnostic_hit:
            device.is_active = True
            is_active_reason = active_hit or therapeutic_hit or diagnostic_hit
            signals.append(f"is_active = True (matched: {is_active_reason.label})")
            if therapeutic_hit:
                device.active_type = ActiveDeviceType.THERAPEUTIC
                signals.append(f"active_type = THERAPEUTIC (matched: {therapeutic_hit.label})")
            elif diagnostic_hit:
                device.active_type = ActiveDeviceType.DIAGNOSTIC_MONITORING
                signals.append(f"active_type = DIAGNOSTIC_MONITORING (matched: {diagnostic_hit.label})")
            else:
                device.active_type = ActiveDeviceType.OTHER_ACTIVE
                notes.append(
                    "active_type: device is active but no therapeutic/diagnostic signal "
                    "found - defaulted to OTHER_ACTIVE (Rule 13's residual bucket). Verify "
                    "this is correct rather than a missed Rule 9/10 signal."
                )

            # --- Rule 9: administers or exchanges energy ---
            energy_hit = _any_match(text, _ADMINISTERS_EXCHANGES_ENERGY_SIGNALS)
            if energy_hit:
                device.administers_or_exchanges_energy = True
                signals.append(f"administers_or_exchanges_energy = True (matched: {energy_hit.label})")

            therapeutic_radiation_hit = _any_match(text, _IONISING_RADIATION_THERAPEUTIC_SIGNALS)
            if therapeutic_radiation_hit:
                device.emits_ionising_radiation_therapeutic = True
                signals.append(
                    f"emits_ionising_radiation_therapeutic = True (matched: {therapeutic_radiation_hit.label})"
                )

            # --- Rule 10: active diagnostic/monitoring device detail ---
            if device.active_type == ActiveDeviceType.DIAGNOSTIC_MONITORING:
                energy_absorbed_hit = _any_match(text, _DIAGNOSTIC_ENERGY_ABSORBED_SIGNALS)
                if energy_absorbed_hit:
                    device.diagnostic_supplies_energy_absorbed_by_body = True
                    signals.append(
                        f"diagnostic_supplies_energy_absorbed_by_body = True (matched: {energy_absorbed_hit.label})"
                    )
                illuminate_hit = _any_match(text, _DIAGNOSTIC_ILLUMINATE_SIGNALS)
                if illuminate_hit:
                    device.diagnostic_illuminates_patient_visible_spectrum_only = True
                    signals.append(
                        f"diagnostic_illuminates_patient_visible_spectrum_only = True (matched: {illuminate_hit.label})"
                    )
                radiopharm_hit = _any_match(text, _RADIOPHARMACEUTICAL_SIGNALS)
                if radiopharm_hit:
                    device.diagnostic_images_in_vivo_radiopharmaceutical_distribution = True
                    signals.append(
                        f"diagnostic_images_in_vivo_radiopharmaceutical_distribution = True (matched: {radiopharm_hit.label})"
                    )
                direct_diag_hit = _any_match(text, _DIRECT_DIAGNOSIS_VITAL_SIGNALS)
                if direct_diag_hit:
                    device.diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes = True
                    signals.append(
                        f"diagnostic_allows_direct_diagnosis_or_monitoring_of_vital_physiological_processes = True "
                        f"(matched: {direct_diag_hit.label})"
                    )
                    danger_hit = _any_match(text, _IMMEDIATE_DANGER_SIGNALS)
                    if danger_hit:
                        device.diagnostic_variation_could_cause_immediate_danger = True
                        signals.append(
                            f"diagnostic_variation_could_cause_immediate_danger = True (matched: {danger_hit.label})"
                        )
                    else:
                        questions.append(
                            "This appears to be a device for direct diagnosis or monitoring of "
                            "vital physiological processes. Per Rule 10, if the nature of "
                            "variations in what it monitors 'could result in immediate danger to "
                            "the patient' (the regulation's own examples: cardiac performance, "
                            "respiration, activity of the central nervous system), it is Class "
                            "IIb rather than the default Class IIa. Please specify whether this "
                            "applies, or consult a regulatory professional."
                        )

            # --- Rule 12: administers/removes substances to/from the body ---
            admin_remove_hit = _any_match(text, _ADMINISTERS_OR_REMOVES_SUBSTANCES_SIGNALS)
            if admin_remove_hit:
                device.administers_or_removes_substances_to_from_body = True
                signals.append(
                    f"administers_or_removes_substances_to_from_body = True (matched: {admin_remove_hit.label})"
                )

            # --- Rule 22: active therapeutic device with integrated diagnostic function ---
            closed_loop_hit = _any_match(text, _CLOSED_LOOP_AED_SIGNALS)
            if closed_loop_hit:
                device.is_active_therapeutic_with_integrated_diagnostic_function = True
                signals.append(
                    f"is_active_therapeutic_with_integrated_diagnostic_function = True "
                    f"(matched: {closed_loop_hit.label})"
                )

        # --- Rule 10 (continued): diagnostic/interventional ionising radiation.
        # Gated on is_active alone (not DIAGNOSTIC_MONITORING specifically) per
        # the rule's own text, which covers "diagnostic or therapeutic
        # radiology" devices generally. ---
        if device.is_active:
            radiology_hit = _any_match(text, _DIAGNOSTIC_THERAPEUTIC_RADIOLOGY_SIGNALS)
            if radiology_hit:
                device.emits_ionising_radiation_diagnostic_or_interventional = True
                signals.append(
                    f"emits_ionising_radiation_diagnostic_or_interventional = True (matched: {radiology_hit.label})"
                )

        software_hit = apply_bool("is_software", _SOFTWARE_SIGNALS)
        if software_hit:
            decision_hit = _any_match(text, _SOFTWARE_DECISION_SUPPORT_SIGNALS)
            monitor_hit = _any_match(text, _SOFTWARE_MONITORING_SIGNALS)

            if decision_hit:
                death_hit = _any_match(text, _SOFTWARE_SEVERITY_DEATH_SIGNALS)
                serious_hit = _any_match(text, _SOFTWARE_SEVERITY_SERIOUS_SIGNALS)
                if death_hit:
                    device.software_decision_impact = SoftwareDecisionImpact.DEATH_OR_IRREVERSIBLE_DETERIORATION
                    signals.append(
                        f"software_decision_impact = DEATH_OR_IRREVERSIBLE_DETERIORATION "
                        f"(decision-support function matched: {decision_hit.label}; "
                        f"severity matched: {death_hit.label})"
                    )
                elif serious_hit:
                    device.software_decision_impact = SoftwareDecisionImpact.SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION
                    signals.append(
                        f"software_decision_impact = SERIOUS_DETERIORATION_OR_SURGICAL_INTERVENTION "
                        f"(decision-support function matched: {decision_hit.label}; "
                        f"severity matched: {serious_hit.label})"
                    )
                else:
                    # Function detected, severity unknown: set the
                    # conservative FLOOR the detected function alone
                    # supports (IIa), never the "all other software"
                    # bucket (I) - and ask exactly what would raise it.
                    device.software_decision_impact = SoftwareDecisionImpact.OTHER_IMPACT
                    signals.append(
                        f"software_decision_impact = OTHER_IMPACT (conservative floor: "
                        f"decision-support function matched ({decision_hit.label}), but no "
                        f"severity signal found - see clarifying question)"
                    )
                    questions.append(
                        "This appears to be decision-support/diagnostic software "
                        f"(detected: '{decision_hit.label}'). Per Annex VIII Rule 11, its "
                        "class depends on the worst realistic consequence if its output is "
                        "wrong or delayed: (a) routine/no significant risk -> Class IIa "
                        "[current provisional result]; (b) serious deterioration of health "
                        "or need for surgical intervention -> Class IIb; (c) death or "
                        "irreversible deterioration -> Class III. MDCG guidance treats this "
                        "as a clinical-judgement call, not a mechanical one (see "
                        "docs/CLARIFICATIONS_RULE_11.md) - please specify which applies, or "
                        "take this exact question to a regulatory professional."
                    )

            if monitor_hit:
                device.software_monitors_physiological_processes = True
                signals.append(f"software_monitors_physiological_processes = True (matched: {monitor_hit.label})")
                danger_hit = _any_match(text, _SOFTWARE_VITAL_DANGER_SIGNALS)
                if danger_hit:
                    device.software_monitors_vital_parameters_with_immediate_danger_potential = True
                    signals.append(
                        f"software_monitors_vital_parameters_with_immediate_danger_potential = True "
                        f"(matched: {danger_hit.label})"
                    )
                else:
                    questions.append(
                        "This appears to be physiological-monitoring software. Per MDCG "
                        "2021-24, the same monitoring function is Class IIa in routine/home "
                        "use but Class IIb if used for continuous surveillance in "
                        "anaesthesia, intensive care, or emergency care (see "
                        "docs/CLARIFICATIONS_RULE_11.md). Please specify the intended "
                        "clinical context, or take this question to a regulatory "
                        "professional. [current provisional result: Class IIa]"
                    )

            if not decision_hit and not monitor_hit:
                notes.append(
                    "is_software = True, and no decision-support or monitoring function was "
                    "detected in the text - treated as 'all other software' (Rule 11 -> Class "
                    "I). If this software DOES inform a diagnosis/treatment decision or "
                    "monitor physiological processes, describe that explicitly; otherwise "
                    "this result should be correct."
                )

        # --- Class I sub-qualifiers ---
        apply_bool("placed_on_market_sterile", _STERILE_SIGNALS)
        apply_bool("has_measuring_function", _MEASURING_SIGNALS)
        apply_bool("is_reusable_surgical_instrument", _REUSABLE_INSTRUMENT_SIGNALS)

        # --- Critical anatomy ---
        apply_bool("contacts_heart_or_central_circulatory_system", _HEART_CIRC_SIGNALS)
        apply_bool("contacts_central_nervous_system", _CNS_SIGNALS)
        teeth_hit = _any_match(text, _PLACED_IN_TEETH_SIGNALS)
        if teeth_hit:
            device.placed_in_teeth = True
            signals.append(f"placed_in_teeth = True (matched: {teeth_hit.label})")
            # A genuine intra-tooth restoration (filling, crown, bridge) is
            # placed via clinical intervention and remains in place, matching
            # Article 2(5)'s implantable-device definition even though it
            # isn't colloquially called an "implant" - without this,
            # placed_in_teeth alone has no effect because Rule 8's gate
            # (is_implantable or long-term surgically invasive) never fires.
            # See docs/CLARIFICATIONS_RULE_8.md.
            if not device.is_implantable:
                device.is_implantable = True
                signals.append("is_implantable = True (inferred from genuine tooth-structure placement, per Article 2(5))")
        apply_bool("is_joint_replacement", _JOINT_REPLACEMENT_SIGNALS)
        apply_bool("is_spinal_disc_replacement_or_contacts_spinal_column", _SPINAL_SIGNALS)
        apply_bool("is_breast_implant_or_surgical_mesh", _BREAST_MESH_SIGNALS)
        apply_bool("is_active_implantable_or_accessory", _ACTIVE_IMPLANTABLE_SIGNALS)

        # --- Shared Rules 6-8 physical effects ---
        apply_bool("supplies_ionising_radiation", _IONISING_RADIATION_SIGNALS)
        apply_bool("undergoes_chemical_change_in_body", _CHEMICAL_CHANGE_SIGNALS)

        # --- Physical effects / medicinal content ---
        apply_bool("has_biological_effect_or_wholly_mainly_absorbed", _ABSORBABLE_SIGNALS)
        apply_bool("administers_medicinal_product", _ADMINISTERS_MEDICINAL_PRODUCT_SIGNALS)
        apply_bool("contains_ancillary_medicinal_substance", _ANCILLARY_MEDICINAL_SUBSTANCE_SIGNALS)
        apply_bool("is_contraceptive_or_sti_prevention", _CONTRACEPTIVE_SIGNALS)
        apply_bool("is_xray_diagnostic_image_recording_device", _XRAY_RECORDING_SIGNALS)
        apply_bool("contains_nanomaterial", _NANOMATERIAL_SIGNALS)

        inhalation_hit = apply_bool("administers_medicinal_product_by_inhalation", _INHALATION_SIGNALS)
        if inhalation_hit:
            life_threat_hit = _any_match(text, _INHALATION_LIFE_THREATENING_SIGNALS)
            if life_threat_hit:
                device.inhalation_essential_impact_or_life_threatening = True
                signals.append(
                    f"inhalation_essential_impact_or_life_threatening = True (matched: {life_threat_hit.label})"
                )

        # --- Rule 16: disinfecting/cleaning/rinsing/hydrating/sterilising ---
        lens_care_hit = _any_match(text, _DISINFECT_CONTACT_LENS_SIGNALS)
        invasive_endpoint_hit = _any_match(text, _DISINFECT_INVASIVE_ENDPOINT_SIGNALS)
        other_device_hit = _any_match(text, _DISINFECT_OTHER_DEVICE_SIGNALS)
        physical_only_hit = _any_match(text, _PHYSICAL_ACTION_ONLY_SIGNALS)
        if lens_care_hit:
            device.disinfect_clean_target = DisinfectCleanTarget.CONTACT_LENSES
            signals.append(f"disinfect_clean_target = CONTACT_LENSES (matched: {lens_care_hit.label})")
        elif invasive_endpoint_hit:
            device.disinfect_clean_target = DisinfectCleanTarget.INVASIVE_DEVICE_END_POINT
            signals.append(f"disinfect_clean_target = INVASIVE_DEVICE_END_POINT (matched: {invasive_endpoint_hit.label})")
        elif other_device_hit and physical_only_hit:
            device.disinfect_clean_target = DisinfectCleanTarget.PHYSICAL_ACTION_ONLY_NON_LENS
            signals.append(
                f"disinfect_clean_target = PHYSICAL_ACTION_ONLY_NON_LENS (matched: "
                f"{other_device_hit.label} + {physical_only_hit.label}) - Rule 16 carve-out, does not apply"
            )
        elif other_device_hit:
            device.disinfect_clean_target = DisinfectCleanTarget.OTHER_MEDICAL_DEVICE
            signals.append(f"disinfect_clean_target = OTHER_MEDICAL_DEVICE (matched: {other_device_hit.label})")

        # --- Tissue origin (Rule 18) ---
        animal_hit = _any_match(text, _TISSUE_ANIMAL_SIGNALS)
        human_hit = _any_match(text, _TISSUE_HUMAN_SIGNALS)
        if animal_hit:
            device.contains_human_or_animal_tissue_or_cells = True
            device.tissue_origin = TissueOrigin.ANIMAL
            signals.append(f"contains_human_or_animal_tissue_or_cells = True, tissue_origin = ANIMAL (matched: {animal_hit.label})")
        elif human_hit:
            device.contains_human_or_animal_tissue_or_cells = True
            device.tissue_origin = TissueOrigin.HUMAN
            signals.append(f"contains_human_or_animal_tissue_or_cells = True, tissue_origin = HUMAN (matched: {human_hit.label})")
        if device.contains_human_or_animal_tissue_or_cells:
            intact_skin_hit = _any_match(text, _INTACT_SKIN_ONLY_SIGNALS)
            if intact_skin_hit:
                device.tissue_contacts_intact_skin_only = True
                signals.append(f"tissue_contacts_intact_skin_only = True (matched: {intact_skin_hit.label})")

        # --- Rule 21: substance-based devices absorbed/dispersed via orifice or skin ---
        substance_hit = _any_match(text, _SUBSTANCE_ABSORBED_DISPERSED_SIGNALS)
        if substance_hit:
            device.composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin = True
            signals.append(
                f"composed_of_substances_absorbed_or_dispersed_via_orifice_or_skin = True "
                f"(matched: {substance_hit.label})"
            )
            not_systemic_hit = _any_match(text, _NOT_SYSTEMICALLY_ABSORBED_SIGNALS)
            systemic_hit = _any_match(text, _SYSTEMICALLY_ABSORBED_SIGNALS)
            if not_systemic_hit:
                device.systemically_absorbed = False
                signals.append(f"systemically_absorbed = False (matched: {not_systemic_hit.label})")
            elif systemic_hit:
                device.systemically_absorbed = True
                signals.append(f"systemically_absorbed = True (matched: {systemic_hit.label})")
            gi_hit = _any_match(text, _STOMACH_LOWER_GI_SIGNALS)
            if gi_hit:
                device.achieves_purpose_in_stomach_or_lower_gi_tract = True
                signals.append(f"achieves_purpose_in_stomach_or_lower_gi_tract = True (matched: {gi_hit.label})")
            applied_hit = _any_match(text, _APPLIED_SKIN_NASAL_ORAL_PHARYNX_SIGNALS)
            if applied_hit:
                device.applied_to_skin_or_nasal_oral_cavity_to_pharynx = True
                signals.append(
                    f"applied_to_skin_or_nasal_oral_cavity_to_pharynx = True (matched: {applied_hit.label})"
                )

        # --- Wound contact (Rule 4) ---
        wound_gate_hit = _any_match(text, _WOUND_CONTACT_GATE_SIGNALS)
        if wound_gate_hit:
            device.contacts_injured_skin_or_mucous_membrane = True
            signals.append(f"contacts_injured_skin_or_mucous_membrane = True (matched: {wound_gate_hit.label})")

            breached_hit = _any_match(text, _WOUND_BREACHED_DERMIS_SIGNALS)
            micro_hit = _any_match(text, _WOUND_MICROENVIRONMENT_SIGNALS)
            barrier_hit = _any_match(text, _WOUND_BARRIER_SIGNALS)
            # Per MDCG 2021-24 (docs/CLARIFICATIONS_RULE_4.md), highest class
            # wins when a device description matches more than one purpose,
            # so check in class-descending order: breached dermis (IIb) >
            # micro-environment (IIa) > mechanical barrier (I).
            if breached_hit:
                device.wound_contact_purpose = WoundContactPurpose.BREACHED_DERMIS_SECONDARY_INTENT_HEALING
                signals.append(f"wound_contact_purpose = BREACHED_DERMIS_SECONDARY_INTENT_HEALING (matched: {breached_hit.label})")
            elif micro_hit:
                device.wound_contact_purpose = WoundContactPurpose.MANAGE_MICROENVIRONMENT
                signals.append(f"wound_contact_purpose = MANAGE_MICROENVIRONMENT (matched: {micro_hit.label})")
            elif barrier_hit:
                device.wound_contact_purpose = WoundContactPurpose.MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION
                signals.append(f"wound_contact_purpose = MECHANICAL_BARRIER_COMPRESSION_OR_ABSORPTION (matched: {barrier_hit.label})")
            else:
                device.wound_contact_purpose = WoundContactPurpose.OTHER
                notes.append(
                    "wound_contact_purpose: wound/dressing context found but no specific "
                    "purpose signal - defaulted to OTHER (Rule 4's IIa catch-all). Verify "
                    "against the device's actual stated intended purpose."
                )

        return ExtractionResult(
            device=device,
            matched_signals=signals,
            unmatched_notes=notes,
            clarifying_questions=questions,
        )
