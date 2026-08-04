# Clarification: Rule 4 (contact with injured skin or mucous membrane)

## Status: resolved at the engine level; open question moved to Phase 2

This rule was originally flagged in this engine as an "ambiguous judgement
call" because its four bullets read as a parallel descriptive list rather
than a base-rule-with-exceptions (contrast Rules 6-8). Verifying against
actual regulatory guidance (below) shows that characterisation was only
half right: **the precedence question is not ambiguous** - official
guidance directly confirms this engine's "highest class wins" logic.
**What actually is a judgement call has moved upstream**, to determining
a device's intended purpose from a free-text description, which is a
Phase 2 (extraction) problem, not something Rule 4's logic itself needs
to resolve.

## The regulation (Annex VIII, 4.4)

> "All non-invasive devices which come into contact with injured skin or
> mucous membrane are classified as: - class I if they are intended to be
> used as a mechanical barrier, for compression or for absorption of
> exudates; - class IIb if they are intended to be used principally for
> injuries to skin which have breached the dermis or mucous membrane and
> can only heal by secondary intent; - class IIa if they are principally
> intended to manage the micro-environment of injured skin or mucous
> membrane; and - class IIa in all other cases. This rule applies also to
> the invasive devices that come into contact with injured mucous
> membrane."

Read literally, this is four bullets with no explicit "unless X, in
which case Y" ranking between them - unlike, say, Rule 6 or Rule 8.

## What official guidance says

**Source:** MDCG 2021-24 Rev.1, *"Guidance on classification of medical
devices"* (Medical Device Coordination Group, established under Article
103 of Regulation (EU) 2017/745), pages 32-33.
Retrieved from `https://health.ec.europa.eu/system/files/2021-10/mdcg_2021-24_en_0.pdf`
on 2026-08-04. Full extracted text saved at
[`docs/legal_sources/mdcg_2021-24_rule_4_wound_dressings.txt`](legal_sources/mdcg_2021-24_rule_4_wound_dressings.txt)
for audit.

> Note on legal weight, quoting the document itself: *"The document is
> not a European Commission document, and it cannot be regarded as
> reflecting the official position of the European Commission. Any views
> expressed in this document are not legally binding and only the Court
> of Justice of the European Union can give binding interpretations of
> Union law."* MDCG guidance is not law - but it is what notified bodies
> actually use day to day, and it is the closest thing to an
> authoritative interpretation that exists short of a CJEU ruling.

### On precedence between bullets (this resolves the original ambiguity flag)

> "The classification of devices covered by this rule depends on the use
> intended by the manufacturer's, e.g. a polymeric film dressing would be
> in class IIa if the intended use is to manage the micro-environment of
> the wound or in class I if its intended use is limited to retaining an
> invasive cannula at the wound site. Consequently, it is impossible to
> say a priori that a particular type of dressing belongs to a given
> class without knowing its intended use as defined by the manufacturer.
> However, a claim that the device is interactive or active with respect
> to the wound healing process usually implies that the device is at
> least class IIa."
>
> "**Most dressings that are intended for a use that falls under class
> IIa or IIb also perform functions that are in class I, e.g. that of a
> mechanical barrier. Such devices are nevertheless classified according
> to their intended use in the higher class.**"

That second paragraph is a direct, official statement of exactly the
"highest matched bullet wins" logic this engine implements in
`Rule4.evaluate()` via `_evaluate_candidates()`. It is not this project's
interpretive choice - it is what MDCG says notified bodies actually do.
**The `RuleOutcome.ambiguous` flag has been removed from `Rule4` for this
reason** (see `rules_engine/eu_mdr/rules.py`).

### On rules that take precedence over Rule 4 entirely

> "Dressings incorporating a substance which, if used separately, can be
> considered to be a medicinal product and that has an action ancillary
> to that of the dressing, fall within class III under Rule 14. Devices
> composed of other substances which are absorbed by or locally dispersed
> in the human body fall under Rule 21."
>
> "For such devices incorporating a substance which, if used separately,
> can be considered to be medicinal product or a human blood derivative,
> or animal tissues or derivatives rendered non-viable, see Rule 14 or
> Rule 18 respectively."

This confirms the engine's cross-rule "highest wins" behaviour (Annex
VIII 3.5, implemented in `EUMDRClassificationEngine.classify()`) is the
correct mechanism here too: a silver-releasing or drug-eluting dressing
should trigger Rule 14 (Class III) or Rule 21 alongside Rule 4, and the
engine already takes the max across all triggered rules - no special
case needed.

### Worked examples (verbatim from MDCG 2021-24, pp. 32-33)

| Class | Examples given |
|---|---|
| **I** | Absorbent pads, island dressings, cotton wool, wound strips, adhesive bandages (sticking plasters, band-aid), gauze dressings which act as a barrier / maintain wound position / absorb exudates; ostomy bags |
| **IIb** | Dressings intended for ulcerated wounds having breached the dermis; dressings intended for burns having breached the dermis; dressings for severe decubitus wounds; dressings incorporating means of augmenting tissue and providing a temporary skin substitute |
| **IIa** | Hydrogel dressings for wounds/injuries that have not breached the dermis or can only heal by secondary intent; non-medicated impregnated gauze dressings; polymer film dressings |
| **I** (named exception worth flagging) | **Dressings for nose bleeds** - MDCG explicitly notes "the purpose of the dressing is not to manage micro-environment... are in class I according to this rule," despite nosebleed dressings intuitively sounding like they might need the IIa catch-all. This is a genuinely instructive example: the IIa catch-all is a true residual, not a default for "anything not obviously mechanical" - a device whose function actually *is* absorption (as a nosebleed dressing's is) belongs in the Class I bullet even if nobody explicitly labelled it "mechanical barrier." Also: dental wound dressings not containing animal-derived material. |

These four examples have been added verbatim to
[`tests/test_known_devices.py`](../tests/test_known_devices.py) as
ground-truth cases, citing MDCG 2021-24 in the test names.

### Definitions (MDCG 2021-24, p. 33)

> "**Breached dermis or mucosa:** the wound exposes at least partly the
> subcutaneous tissue."
>
> "**Secondary intent:** the wound heals by first being filled with
> granulation tissue; subsequently the epithelium grows back over the
> granulation tissue and the wound contracts. In contrast, primary intent
> implies that the edges of the wound are close enough or pulled
> together, e.g. by suturing, to allow the wound to heal before formation
> of granulation tissue."

These are useful for a future extraction layer: text mentioning
"breached dermis," "full-thickness wound," "exposed subcutaneous
tissue," or "heals by granulation" should map to
`wound_contact_purpose = BREACHED_DERMIS_SECONDARY_INTENT_HEALING`.

## What this means for Phase 2 (extraction)

The genuinely unresolved question, per MDCG's own words, is: **"it is
impossible to say a priori that a particular type of dressing belongs to
a given class without knowing its intended use as defined by the
manufacturer."**

That is an extraction-layer problem: given a free-text device
description, how does the extractor decide which single
`wound_contact_purpose` value to populate? Some guidance for that future
work:

1. **Look for explicit intended-purpose language first** ("intended to
   manage the wound micro-environment," "intended as a mechanical
   barrier," "for wounds healing by secondary intent") - MDCG's own
   phrasing is a good keyword source.
2. **A claim of "interactive" or "active" wound-healing involvement
   defaults to at least Class IIa** per MDCG's explicit statement above -
   this is a safe conservative default when purpose is unclear but the
   product is clearly not "purely passive."
3. **Absence of an explicit microenvironment/healing claim defaults to
   the Class I bullet** if the description is otherwise consistent with
   simple barrier/absorption function (per the nosebleed dressing
   example) - do not default to the IIa catch-all just because a device
   "doesn't sound purely mechanical."
4. **Check for medicinal substances or tissue content first** - if the
   description mentions silver, antimicrobial agents, growth factors, or
   animal/human tissue-derived material, route to Rule 14/18/21 checks
   before finalizing Rule 4's `wound_contact_purpose`, since those rules
   commonly dominate the final class via cross-rule precedence anyway.

## Summary

| Question | Answer |
|---|---|
| Is Rule 4's bullet precedence ambiguous? | **No** - MDCG 2021-24 confirms "highest class wins," matching this engine's implementation exactly. |
| Is anything about Rule 4 still a judgement call? | **Yes** - identifying the manufacturer's *intended purpose* from a device description, which is Phase 2's job, not this rule's. |
| Does the engine need to change? | No logic change; the `ambiguous` flag was removed from `Rule4`'s `RuleOutcome` since it no longer applies at this layer. |
| Are there real worked examples now in the test suite? | Yes - four MDCG-sourced examples added to `tests/test_known_devices.py`. |
