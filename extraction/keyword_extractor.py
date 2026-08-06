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

This extractor targets a deliberately bounded, documented subset of
``rules_engine.models.DeviceAttributes`` - the fields most reliably
signalled by short free-text device descriptions. It does NOT attempt
every field on the model. Covered:

- invasiveness, duration, is_implantable, is_active, active_type,
  is_software (including decision-support/monitoring *function*
  detection - see "Software" below), drives_or_influences_device_class
  (never inferred - always left None; genuinely requires knowing about
  a separate device)
- placed_on_market_sterile, has_measuring_function,
  is_reusable_surgical_instrument
- contacts_heart_or_central_circulatory_system,
  contacts_central_nervous_system, placed_in_teeth,
  is_joint_replacement, is_spinal_disc_replacement_or_contacts_spinal_column,
  is_breast_implant_or_surgical_mesh, is_active_implantable_or_accessory
- has_biological_effect_or_wholly_mainly_absorbed,
  administers_medicinal_product, contains_ancillary_medicinal_substance
- contacts_injured_skin_or_mucous_membrane, wound_contact_purpose
- is_contraceptive_or_sti_prevention,
  is_xray_diagnostic_image_recording_device,
  contains_human_or_animal_tissue_or_cells, tissue_origin,
  contains_nanomaterial, administers_medicinal_product_by_inhalation

NOT covered (left at DeviceAttributes defaults - see that module for the
full field list): the Rule 2/3 non-invasive channelling/modification
detail (storage_target, modification_treatment_type), Rule 5's body-
orifice-site/absorption nuances, Rule 9/10's fine-grained active-device
energy/diagnostic sub-conditions, Rule 16's disinfection-target detail,
Rule 19's nanomaterial exposure tier, Rule 20/21's hazard/absorption-
site nuances, and the ancillary-component / ancillary-medicinal-
substance-vs-primary-action distinctions that MDCG itself says need
case-by-case judgement (see docs/CLARIFICATIONS_RULE_8.md).

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
    DeviceAttributes,
    Duration,
    Invasiveness,
    SoftwareDecisionImpact,
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
    _Signal(r"\bbattery|\bbatteries\b", "battery-powered"),
    _Signal(r"\bpowered\b", "powered"),
    _Signal(r"\belectronic", "electronic"),
    _Signal(r"\belectric(?:al)?\b", "electric(al)"),
    _Signal(r"\brechargeable", "rechargeable"),
    _Signal(r"\benergy source", "energy source"),
    _Signal(r"\bmotor(?:ised|ized)?\b", "motor(ised)"),
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
    _Signal(r"\bimaging\b|\bscanner\b", "imaging/scanner"),
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
_HEART_CIRC_SIGNALS = [
    _Signal(r"\bheart\b|\bcardiac\b|\bcoronary\b", "heart/cardiac/coronary"),
    _Signal(r"\baorta\b|\bcirculatory system\b|\bvena cava\b|\bpulmonary artery\b", "central circulatory system"),
]
_CNS_SIGNALS = [
    _Signal(r"\bbrain\b|\bcerebral\b", "brain/cerebral"),
    _Signal(r"\bspinal cord\b|\bcentral nervous system\b|\bcns\b", "spinal cord / CNS"),
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
    _Signal(r"\b(?:implantable )?(?:cardioverter )?defibrillator|\bicd\b", "implantable cardioverter defibrillator"),
    _Signal(r"\bcochlear implant", "cochlear implant"),
    _Signal(r"\b(?:neuro|nerve) ?stimulator", "neuro/nerve stimulator"),
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

        # --- Implantable / active / software ---
        apply_bool("is_implantable", _IMPLANTABLE_SIGNALS)

        active_hit = _any_match(text, _ACTIVE_SIGNALS)
        if active_hit:
            device.is_active = True
            signals.append(f"is_active = True (matched: {active_hit.label})")
            therapeutic_hit = _any_match(text, _ACTIVE_THERAPEUTIC_SIGNALS)
            diagnostic_hit = _any_match(text, _ACTIVE_DIAGNOSTIC_SIGNALS)
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

        # --- Physical effects / medicinal content ---
        apply_bool("has_biological_effect_or_wholly_mainly_absorbed", _ABSORBABLE_SIGNALS)
        apply_bool("administers_medicinal_product", _ADMINISTERS_MEDICINAL_PRODUCT_SIGNALS)
        apply_bool("contains_ancillary_medicinal_substance", _ANCILLARY_MEDICINAL_SUBSTANCE_SIGNALS)
        apply_bool("is_contraceptive_or_sti_prevention", _CONTRACEPTIVE_SIGNALS)
        apply_bool("is_xray_diagnostic_image_recording_device", _XRAY_RECORDING_SIGNALS)
        apply_bool("contains_nanomaterial", _NANOMATERIAL_SIGNALS)
        apply_bool("administers_medicinal_product_by_inhalation", _INHALATION_SIGNALS)

        # --- Tissue origin ---
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
