# MedTech Device Regulatory Classifier

> **This is an educational/demonstration tool, not real regulatory or legal
> advice.** It is a portfolio project demonstrating a deterministic,
> auditable rules engine built against the real text of Regulation (EU)
> 2017/745. Always consult a notified body or regulatory professional for
> an actual device classification.

## What this is

A tool that takes information about a medical device and predicts its EU
MDR 2017/745 risk classification (Class I / Is / Im / Ir / IIa / IIb /
III), citing exactly which Annex VIII rule(s) triggered the result and
why.

**The classification logic is not an LLM guessing an answer.** It is
explicit, unit-tested Python code implementing Annex VIII Rules 1-22 and
the precedence logic that governs them, written directly against the
verbatim text of Regulation (EU) 2017/745 fetched from EUR-Lex (see
`docs/legal_sources/`). The only place free text is involved at all is
the extraction layer (Phase 2, below) that turns a description into
structured input - the classification decision itself is always this
deterministic engine, never an LLM, and never the extractor's own
judgement.

## Phase 1: the rules engine (done)

- `rules_engine/models.py` - the structured `DeviceAttributes` input
  model, `DeviceClass` / `RuleOutcome` / `ClassificationResult` types.
- `rules_engine/base.py` - jurisdiction-agnostic `ClassificationRule` and
  `ClassificationEngine` interfaces (the extension point a future UK
  MDR/UKCA engine would implement).
- `rules_engine/eu_mdr/rules.py` - Rules 1-22, each its own class citing
  the Annex VIII section it implements.
- `rules_engine/eu_mdr/engine.py` - evaluates all 22 rules and applies
  Annex VIII 3.5's "highest classification wins" precedence, plus the
  Article 52(7) Is/Im/Ir sub-qualifiers.

## Phase 2: free-text extraction (done)

- `extraction/base.py` - the `Extractor` interface and `ExtractionResult`
  (a `DeviceAttributes` plus a human-readable log of exactly which words
  triggered which field, and which fields it could not determine). Kept
  method-agnostic so a future LLM-based extractor could implement the
  same interface without the rules engine or CLI caring which produced
  its input.
- `extraction/keyword_extractor.py` - `KeywordExtractor`, the **default**
  extractor per the project brief (keyword/rule-based is the lead path,
  not a fallback for an LLM). Covers **56 of 65** `DeviceAttributes`
  fields (86%), each grounded in the exact Article 2 / Annex VIII
  provision it implements - not invented synonyms. The remaining 9 are
  left uncovered on purpose, in two honest categories: fields that
  describe a relationship to a *second* device this extractor has no
  knowledge of (e.g. `drives_or_influences_device_class`), and genuine
  "potentially hazardous" / technical-assessment judgement calls MDCG's
  own guidance says can't be reduced to a checklist (e.g.
  `is_ancillary_component`, `nanomaterial_internal_exposure_potential` -
  see `docs/CLARIFICATIONS_RULE_8.md` and `docs/CLARIFICATIONS_RULE_11.md`).
  See the module's own docstring for the itemised list.
- `cli.py --text "..."` - runs a description through the extractor, then
  the same engine as the structured-input path, printing both the
  matched signals (why it concluded what it did) and anything it could
  not determine.
- **Full transparency by default**: `cli.py`'s human-readable report
  shows the status of all 22 rules, not just the deciding one - a Class
  I result visibly means "we checked everything and only Rule 1's
  default applied," not a silent absence of information.
- **Clarifying questions, not just warnings, for genuine judgement
  calls**: when the extractor detects decision-support or monitoring
  *function* in software (or vital-parameter danger context) but can't
  determine severity from text alone, it never lets that fall into Rule
  11's "all other software" bucket by omission - it sets the
  conservative floor the detected function actually supports and asks
  the specific question (with each answer's consequence named) needed to
  finish the job. See `ExtractionResult.clarifying_questions`.
- Keyword lists are grounded directly in the regulation's own defining
  vocabulary rather than invented synonyms wherever a definition exists -
  e.g. Annex VIII 2.6 gives an exhaustive, exact list of named blood
  vessels for "central circulatory system" (not just "heart"), and 2.3
  defines "reusable surgical instrument" via the verbs "cutting,
  drilling, sawing, scratching, scraping, clamping, retracting,
  clipping," which are now literal signals, not just nouns like
  "scalpel."
- Real bugs found and fixed by this extractor's own test suite before
  commit (documented alongside their fixes in `tests/test_extraction.py`):
  an `\belectrical` regex that missed plain "electric"; a dental-filling
  case where `placed_in_teeth` alone had no effect because Rule 8's gate
  never fired; literal "active device" phrasing not being recognised at
  all (only indirect power-source words were); an automated *external*
  defibrillator (AED) falsely matching the *implantable* cardioverter
  defibrillator signal; and two negation bugs where "not liable to be
  absorbed" / "not systemically absorbed" matched their own positive
  signal because the negated phrase contains it as a substring.

**Not yet built**: standards mapping (`standards_mapper/`) and the
Streamlit UI (`ui/`). Their package directories exist as placeholders
only.

## Regulatory grounding

Every rule was written against text fetched directly from primary and
official sources, saved verbatim in `docs/legal_sources/` - never
reconstructed from memory:

**EUR-Lex (the regulation itself, CELEX:32017R0745)**, retrieved
2026-08-02:
- `annex_viii_classification_rules.txt` - the full Annex VIII text
  (Chapter I definitions, Chapter II implementing rules including the
  3.5 precedence principle, Chapter III Rules 1-22).
- `article_2_definitions_extract.txt` - the Article 2 definitions
  ("active device", "implantable device", "invasive device", etc.) the
  rules' gating logic depends on.
- `article_51_and_52_7_classification_and_subqualifiers.txt` - the legal
  basis for classification itself (Article 51) and the informal
  Is/Im/Ir sub-qualifiers (Article 52(7)).

**MDCG 2021-24 Rev.1** (official guidance interpreting the above,
published by the Medical Device Coordination Group), retrieved
2026-08-04: `mdcg_2021-24_rule_*.txt` - worked examples and precedence
clarifications for every one of the 22 rules, used both to verify the
four originally-flagged ambiguous rules and to fill ground-truth test
coverage for the rest. See **[docs/CLARIFICATIONS.md](docs/CLARIFICATIONS.md)**
for the full verification writeup, including a documented correction
where an earlier unverified pass cited a nonexistent source before this
process was tightened up.

## Precedence logic

Annex VIII Chapter II, point 3.5:

> "If several rules, or if, within the same rule, several sub-rules,
> apply to the same device based on the device's intended purpose, the
> strictest rule and sub-rule resulting in the higher classification
> shall apply."

This is implemented at two levels:

1. **Within a rule** - each rule class evaluates every clause of its
   own text and returns the highest class among whichever clauses
   matched (see `_evaluate_with_base` / `_evaluate_candidates` in
   `rules_engine/eu_mdr/rules.py`).
2. **Across rules** - `EUMDRClassificationEngine.classify()` evaluates
   all 22 rules and takes the highest class among every rule that
   applied.

The **Is / Im / Ir** qualifiers are a separate concern: Article 52(7),
not Annex VIII, so they never affect which base class (I/IIa/IIb/III) is
chosen - they are only computed and attached when the final class is I.

## Rules flagged as genuine judgement calls

The brief for this project explicitly asked not to force false
confidence where the regulation's text does not resolve a question
mechanically. Four rules (4, 8, 11, 18) were originally flagged this way
from the raw EUR-Lex text alone. Each was then checked against actual
MDCG guidance (fetched, extracted, and cited with page numbers - see
**[docs/CLARIFICATIONS.md](docs/CLARIFICATIONS.md)** for the full
verification writeup and methodology):

- **Rule 4** (wound contact) - **resolved**. Official guidance confirms
  this engine's "highest class wins" precedence is correct, not an
  interpretive choice; the `ambiguous` flag was removed.
- **Rule 8**'s "ancillary component" carve-out - **partially resolved**.
  Real named examples exist (pedicle screws, spinal fixation hooks), but
  guidance is explicit that there's no blanket rule - still flagged.
- **Rule 11** (software) severity tiering - **partially resolved**.
  Confirmed genuinely context-dependent (the same function can be a
  different class in ICU vs. home use) with real worked examples; still
  flagged. Also surfaced a separate implementation gap - Annex VIII 3.3
  ("software driving a device inherits its class") wasn't implemented -
  which has since been fixed (`DeviceAttributes.drives_or_influences_device_class`).
- **Rule 18**'s animal-tissue/intact-skin carve-out - **fully resolved**.
  The original "regulation doesn't say what class applies" assumption
  was simply wrong; guidance gives a direct answer (Class I via Rule 1).
  This was the largest correction of the four.

A fifth case is documented but not flagged as ambiguous because it's a
modelling choice rather than a legal one: `tests/test_known_devices.py`
includes a worked example (ECG electrodes) showing a case where this
engine's strict literal reading of Annex VIII diverges from a commonly
published industry classification figure, and explains why.

All 22 Annex VIII rules now have real, MDCG-sourced ground-truth test
cases, and both `rules_engine/eu_mdr/rules.py` and
`extraction/keyword_extractor.py` sit at 100% statement coverage (256
tests total) - see `docs/legal_sources/` for the retrieved source
excerpts behind every citation in this codebase.

## Usage

```bash
pip install -e .
pip install pytest coverage   # dev dependencies, not yet pinned in pyproject

# Structured input (Phase 1) - bypasses extraction entirely
python cli.py examples/hip_implant.json
python cli.py examples/hypodermic_syringe.json --json
echo '{"invasiveness": "non_invasive"}' | python cli.py

# Free text (Phase 2) - runs the default keyword extractor first
python cli.py --text "A sterile, single-use hypodermic syringe used to inject medicinal products under the skin."
python cli.py --text "A titanium hip replacement implant intended for permanent placement." --json

# Run the tests
python -m pytest tests/ -v
```

See `rules_engine/models.py` for the full `DeviceAttributes` field
reference - every field is documented with the Annex VIII rule(s) it
feeds. See `extraction/keyword_extractor.py`'s module docstring for
exactly which of those fields the default extractor attempts to infer
from text, and which it deliberately does not.

## Project layout

```
rules_engine/
  models.py           DeviceAttributes, DeviceClass, RuleOutcome, etc.
  base.py             ClassificationRule / ClassificationEngine interfaces
  eu_mdr/
    rules.py          Rules 1-22
    engine.py          EUMDRClassificationEngine (precedence + qualifiers)
extraction/
  base.py             Extractor interface, ExtractionResult
  keyword_extractor.py  KeywordExtractor - default free-text extractor
cli.py                 CLI harness (structured JSON or --text)
examples/               Sample DeviceAttributes JSON files
tests/                  200 unit tests
docs/legal_sources/     Verbatim EUR-Lex + MDCG source text this was built against
standards_mapper/       Phase 3 placeholder (ISO 10993 / IEC 60601 / etc.)
ui/                     Phase 4 placeholder (Streamlit)
```
