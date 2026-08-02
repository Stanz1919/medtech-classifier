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
`docs/legal_sources/`). A future phase may add an LLM-assisted step that
turns free text into the structured input this engine consumes - but the
classification decision itself will always be this deterministic engine,
never the LLM.

## Phase 1 (current scope)

This repository currently implements **only** the rules engine core:

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
- `cli.py` - a CLI harness that takes a structured attribute dict
  directly (JSON file or stdin), bypassing any text-extraction step.
- `tests/` - 99 unit tests: every rule's branches individually, engine-
  level precedence, and ~30 known real-world device ground-truth cases.

**Not yet built** (later phases): free-text extraction (`extraction/`),
standards mapping (`standards_mapper/`), and the Streamlit UI (`ui/`).
Their package directories exist as placeholders only.

## Regulatory grounding

Every rule was written against text fetched directly from EUR-Lex
(CELEX:32017R0745), saved verbatim in `docs/legal_sources/`:

- `annex_viii_classification_rules.txt` - the full Annex VIII text
  (Chapter I definitions, Chapter II implementing rules including the
  3.5 precedence principle, Chapter III Rules 1-22).
- `article_2_definitions_extract.txt` - the Article 2 definitions
  ("active device", "implantable device", "invasive device", etc.) the
  rules' gating logic depends on.
- `article_51_and_52_7_classification_and_subqualifiers.txt` - the legal
  basis for classification itself (Article 51) and the informal
  Is/Im/Ir sub-qualifiers (Article 52(7)).

Retrieved 2026-08-02.

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
mechanically. Four places are flagged (`RuleOutcome.ambiguous`):

- **Rule 4** (contact with injured skin/mucous membrane) - drafted as a
  parallel list of descriptive bullets rather than a base rule with
  "unless" exceptions, so precedence between overlapping bullets is an
  interpretive choice.
- **Rule 8**'s "ancillary component" carve-out for joint replacements and
  spinal implants - whether a specific part (e.g. a screw) is genuinely
  "ancillary" versus a functional/load-bearing part of the implant is a
  fact-specific judgement notified bodies routinely dispute.
- **Rule 11** (software) severity tiering - classifying decision-support
  software by the severity of harm it *could* cause is one of the most
  contested areas of MDR classification in practice (see MDCG 2019-11).
- **Rule 18**'s animal-tissue/intact-skin-only carve-out - the regulation
  exempts this case from Rule 18 but does not say what class then
  applies.

A fifth case is documented but not flagged as ambiguous because it's a
modelling choice rather than a legal one: `tests/test_known_devices.py`
includes a worked example (ECG electrodes) showing a case where this
engine's strict literal reading of Annex VIII diverges from a commonly
published industry classification figure, and explains why.

## Usage

```bash
pip install -e .
pip install pytest coverage   # dev dependencies, not yet pinned in pyproject

# Run the CLI harness against a structured attribute file
python cli.py examples/hip_implant.json
python cli.py examples/hypodermic_syringe.json --json

# Or pipe JSON in directly
echo '{"invasiveness": "non_invasive"}' | python cli.py

# Run the tests
python -m pytest tests/ -v
```

See `rules_engine/models.py` for the full `DeviceAttributes` field
reference - every field is documented with the Annex VIII rule(s) it
feeds.

## Project layout

```
rules_engine/
  models.py           DeviceAttributes, DeviceClass, RuleOutcome, etc.
  base.py             ClassificationRule / ClassificationEngine interfaces
  eu_mdr/
    rules.py          Rules 1-22
    engine.py          EUMDRClassificationEngine (precedence + qualifiers)
cli.py                 CLI harness
examples/               Sample DeviceAttributes JSON files
tests/                  99 unit tests
docs/legal_sources/     Verbatim EUR-Lex source text this was built against
extraction/             Phase 2 placeholder (free-text -> DeviceAttributes)
standards_mapper/       Phase 3 placeholder (ISO 10993 / IEC 60601 / etc.)
ui/                     Phase 4 placeholder (Streamlit)
```
