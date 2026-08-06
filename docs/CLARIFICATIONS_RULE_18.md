# Clarification: Rule 18 (non-viable human/animal tissue devices)

## Status: resolved - Phase 1's original assumption was wrong

Same verification discipline as Rules 4, 8, and 11: everything below
traces to the actual MDCG 2021-24 Rev.1 PDF, extracted with `pdfplumber`,
pages 53-54. Full extracted text saved at
[`docs/legal_sources/mdcg_2021-24_rule_18_tissue_devices.txt`](legal_sources/mdcg_2021-24_rule_18_tissue_devices.txt).

**This is the most significant correction of the four.** Phase 1's
original code comment (written against EUR-Lex text alone, before any
MDCG guidance was checked) stated: *"The regulation exempts this
animal-tissue/intact-skin-only case from Rule 18 but does not say what
class then applies... flagged rather than assumed."* That was a
reasonable conclusion from the raw legal text in isolation, but it was
**wrong once official guidance is checked** - MDCG resolves this
explicitly and unambiguously.

## The regulation (Annex VIII, 7.5)

> "All devices manufactured utilising tissues or cells of human or
> animal origin, or their derivatives, which are non-viable or rendered
> non-viable, are classified as class III, unless such devices are
> manufactured utilising tissues or cells of animal origin, or their
> derivatives, which are non-viable or rendered non-viable and are
> devices intended to come into contact with intact skin only."

Read in isolation, this says what the carve-out is exempted *from*
(Class III) but not what it *is* instead - which is exactly why Phase 1
flagged it as a gap.

## What official guidance says

**Source:** MDCG 2021-24 Rev.1, pages 53-54.

### The carve-out is resolved directly - Note 3

> "This rule does not apply to devices manufactured utilizing tissues or
> cells of animal origin or their derivatives coming into contact with
> intact skin only. **In such cases they are in class I in accordance to
> Rule 1.** Intact skin includes the skin around an established stoma
> unless the skin is breached."

This is unambiguous: **Class I, via Rule 1**, is the confirmed answer.
Two things worth noting:

1. It explicitly routes through Rule 1 (the non-invasive default), not a
   special classification of its own - consistent with how the carve-out
   devices are intended (contact with intact skin only = non-invasive by
   definition).
2. The "skin around an established stoma" detail is a genuinely useful
   edge case: a stoma is technically a body orifice under Annex VIII
   2.1's definition, but MDCG confirms the *peri-stomal skin* still
   counts as "intact skin" for Rule 18 purposes, as long as that skin
   itself isn't breached.

### Real named examples (verbatim, pp. 53-54)

| Class | Examples |
|---|---|
| **III** | Animal-derived biological heart valves; porcine xenograft dressings; devices made from animal-sourced collagen/gelatine; devices utilising hyaluronic acid of animal origin; substance-based devices containing collagen for use in body orifices; collagen dermal fillers; bone graft substitutes |
| **I** (carve-out) | **Leather components of orthopaedic appliances** |

All eight (seven Class III + the carve-out example) have been added as
named ground-truth cases in `tests/test_known_devices.py`, citing MDCG
2021-24 directly.

### Two further definitional notes worth keeping for Phase 2

**Note 1** - what counts as a "derivative":

> "Derivatives are products that are processed from animal tissues and
> excludes products made by animals e.g. milk, silk, beeswax, honey,
> propolis, royal jelly, hair, lanolin."

**Note 2** - trace processing aids don't trigger the rule, but deliberate
constituents do:

> "The industrial manufacturing process for some devices may employ raw
> materials which contain small amounts of tallow or tallow derivatives
> (e.g. stearates in polymers) for example for greasing the moulds. Such
> substances, which may be present in the final device only as trace
> amounts, are not considered as derivatives of animal tissues for the
> purpose of this rule which therefore does not apply. However, if such
> substances are a constituent part of a device the rule will apply, for
> example wound dressings impregnated with tallow."

This matters for Phase 2's extractor: `contains_human_or_animal_tissue_or_cells`
should only be set `True` for deliberate, functionally-relevant tissue
content - not trace manufacturing residues (mould-release agents, etc.).
A device description mentioning "stearate" as a minor excipient should
not trigger this field; one describing tallow-impregnated gauze should.

## What changed in the code

`Rule18` in `rules_engine/eu_mdr/rules.py` now:
- Directly returns `applies=True, device_class=DeviceClass.I` for the
  carve-out case (previously `applies=False`, relying on `Rule1` to
  independently catch it via cross-rule precedence). This is more
  citation-faithful: the outcome is now traceable to Rule 18's own
  evaluation ("Class I in accordance with Rule 1"), not an implicit
  coincidence of default attribute values.
- No longer sets `ambiguous=True` for the carve-out - it's a resolved,
  cited outcome now, not a judgement call.

Two tests were updated to match, since they had been written against the
old (incorrect) assumption:
- `tests/test_rules_individual.py::test_rule18_animal_tissue_intact_skin_only_carve_out`
  now asserts `Class I`, not "does not apply + ambiguous."
- `tests/test_precedence.py::test_ambiguous_flags_surface_in_final_result`
  used Rule 18's carve-out as its example of an ambiguous flag surfacing
  through the engine. Since Rule 18 is no longer ambiguous, this test was
  switched to use Rule 8's still-genuinely-ambiguous "ancillary
  component" carve-out instead (see `docs/CLARIFICATIONS_RULE_8.md`).

## Summary

| Question | Answer |
|---|---|
| Was Phase 1's "regulatory gap" claim correct? | **No.** MDCG 2021-24 Note 3 resolves it explicitly: Class I via Rule 1. |
| Is the `ambiguous` flag still needed on Rule 18? | **No** - removed. |
| Did the engine's logic need to change? | Yes - the carve-out now directly asserts Class I (citing Rule 1) rather than silently deferring to Rule 1 firing independently. |
| Are there real worked examples now in the test suite? | Yes - 8 MDCG-sourced examples (7 Class III + the leather-orthopaedic-appliance carve-out) added to `tests/test_known_devices.py`. |
| Any modelling guidance for Phase 2? | Yes - don't set `contains_human_or_animal_tissue_or_cells=True` for trace processing residues (Note 2); "intact skin" includes peristomal skin unless breached (Note 3). |

## Running tally: all four originally-flagged rules now checked

| Rule | Outcome |
|---|---|
| Rule 4 | Resolved - precedence confirmed correct; real ambiguity moved to Phase 2 extraction |
| Rule 8 | Partially resolved - real examples found, but MDCG confirms no blanket rule exists; ambiguous flag stays, now with citations |
| Rule 11 | Partially resolved - severity confirmed context-dependent with real examples; separate implementation gap found (Annex VIII 3.3) and filed as a follow-up |
| Rule 18 | **Fully resolved** - Phase 1's "regulatory gap" assumption was simply wrong; MDCG gives a direct, citable answer |
