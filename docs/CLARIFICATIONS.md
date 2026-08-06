# Clarifications: verifying ambiguous Annex VIII rules against real guidance

## What this is

Phase 1 flagged four rules (4, 8, 11, 18) as involving genuine judgement
calls the regulation's text alone doesn't mechanically resolve, per the
brief's instruction not to force false confidence where none is
warranted. This document is the index for the follow-up work that
checked each of those four flags against actual regulatory guidance
rather than leaving them as educated guesses - plus a record of a
mistake made along the way and how it was caught.

Each rule has its own detailed writeup:

| Rule | Doc | Outcome |
|---|---|---|
| Rule 4 (wound contact) | [CLARIFICATIONS_RULE_4.md](CLARIFICATIONS_RULE_4.md) | **Resolved** - precedence confirmed correct; real ambiguity relocated to Phase 2 extraction |
| Rule 8 (ancillary components) | [CLARIFICATIONS_RULE_8.md](CLARIFICATIONS_RULE_8.md) | **Partially resolved** - real examples found, but guidance confirms no blanket rule exists; also caught an unrelated dental-implant modelling risk |
| Rule 11 (software severity) | [CLARIFICATIONS_RULE_11.md](CLARIFICATIONS_RULE_11.md) | **Partially resolved** - severity confirmed context-dependent with real examples; surfaced a separate, genuine implementation gap (Annex VIII 3.3, filed as [Task #15](#known-follow-ups)) |
| Rule 18 (animal tissue/intact skin) | [CLARIFICATIONS_RULE_18.md](CLARIFICATIONS_RULE_18.md) | **Fully resolved** - Phase 1's "regulatory gap" assumption was simply wrong; guidance gives a direct, citable answer |

## Verification methodology

Every claim in these four documents traces to one source, fetched and
read directly rather than paraphrased from training data:

**MDCG 2021-24 Rev.1, "Guidance on classification of medical devices"**
- Published by the Medical Device Coordination Group (established under
  Article 103 of Regulation (EU) 2017/745; composed of representatives
  of all EU Member States, chaired by the European Commission)
- Fetched from `https://health.ec.europa.eu/system/files/2021-10/mdcg_2021-24_en_0.pdf`
- Retrieved and text-extracted with `pdfplumber` on 2026-08-04 - not
  summarized by an intermediate model. Every quote in the four
  clarification docs can be checked against the raw extracted text saved
  in `docs/legal_sources/mdcg_2021-24_*.txt`, with page numbers cited.
- Legal weight, per the document's own disclaimer: *"The document is not
  a European Commission document, and it cannot be regarded as
  reflecting the official position of the European Commission. Any views
  expressed in this document are not legally binding and only the Court
  of Justice of the European Union can give binding interpretations of
  Union law."* It is guidance, not law - but it is what notified bodies
  and manufacturers actually use, and the closest thing to authoritative
  interpretation short of a CJEU ruling.

This same document turned out to cover all 22 Annex VIII rules with
worked examples, not just the four originally flagged ones - so it was
also used to fill the ground-truth gaps described in
[PHASE_2_ROADMAP.md](../PHASE_2_ROADMAP.md) for Rules 3, 10, 12, 13, 14,
16, 20, and 21 (see `docs/legal_sources/mdcg_2021-24_rule_*_examples.txt`
for each).

A second document, **MDCG 2019-11 "Qualification and classification of
software"**, is referenced by MDCG 2021-24 for deeper software-specific
detail but has **not itself been fetched or verified** - only what MDCG
2021-24 quotes from it directly is relied on in this repository. Anyone
extending Rule 11's guidance further should fetch and verify that
document the same way before citing it.

## A correction, kept visible rather than quietly fixed

Before the verified research above, an earlier pass in this project
cited a document called "MDCG 2016-5" and described several "real"
classification disputes - a named manufacturer's hip implant
submission, a silver-dressing notified-body pushback, a bovine-collagen
carve-out dispute - complete with specific outcomes. **None of that was
real.** It was generated as plausible-sounding illustration and
presented as verified fact. When actually searched for, "MDCG 2016-5"
does not exist.

This was caught and disclosed before it was written into any code or
committed documentation - nothing fabricated made it into the repository
- but it's recorded here rather than silently dropped, for two reasons:
it's the reason every claim in the four clarification docs carries a
page number and a locally-saved source excerpt rather than an
unqualified assertion, and it's a more honest record of how this part of
the project actually went than pretending the verified research
appeared fully-formed on the first attempt.

## Known follow-ups

Two items were surfaced by this research and deliberately **not** fixed
inline, since they were out of scope for "verify the four flagged
rules":

1. **Annex VIII Chapter II, point 3.3** ("software which drives a device
   or influences the use of a device shall fall within the same class as
   the device") is not implemented anywhere in this engine. Found while
   reading MDCG 2021-24's Rule 11 section (its Note 3 restates 3.3
   directly). See [CLARIFICATIONS_RULE_11.md](CLARIFICATIONS_RULE_11.md#a-genuine-implementation-gap-this-research-surfaced)
   for the full writeup. Tracked as a task in the project's task list
   ("Implement Annex VIII 3.3: software driving a device inherits its
   class").
2. **Rule 8's "ancillary component" test** remains a genuine judgement
   call with no bright-line rule, per MDCG's own Note 1. The engine
   still flags this (`RuleOutcome.ambiguous`); Phase 2's extractor will
   need explicit guidance for how to populate `is_ancillary_component`
   (see the "What this means for Phase 2" section of
   [CLARIFICATIONS_RULE_8.md](CLARIFICATIONS_RULE_8.md)).

## Where this leaves the rules engine

- All four originally-flagged rules have been checked against real
  guidance; only Rule 8's ancillary-component carve-out and Rule 11's
  severity tiering remain genuinely ambiguous at the engine level (both
  now with real precedent cited, not abstract claims).
- All 22 Annex VIII rules have real-world, MDCG-sourced ground-truth
  test cases (147 tests total, 100% statement coverage on
  `rules_engine/eu_mdr/rules.py`).
- `docs/legal_sources/` now contains, alongside the Phase 1 EUR-Lex
  extracts, sourced excerpts from MDCG 2021-24 for every rule touched by
  this work - the intent is that any specific number, class, or example
  cited anywhere in this codebase's comments or docs can be traced back
  to an actual retrieved document, not reconstructed from memory.
