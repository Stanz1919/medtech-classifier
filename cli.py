#!/usr/bin/env python3
"""CLI harness for the EU MDR 2017/745 classification rules engine.

Two input modes:
  1. Structured attributes (Phase 1) - a JSON object matching
     DeviceAttributes, bypassing extraction entirely. See README.md for
     the field reference and examples/ for sample input files.
  2. Free text (Phase 2) - a device description run through the default
     keyword extractor (extraction.KeywordExtractor) to produce
     DeviceAttributes, then classified exactly the same way. Extraction
     is inherently uncertain (unlike the deterministic rules engine
     downstream of it) - the report always shows which words drove which
     conclusion, and flags anything it could not determine, rather than
     silently guessing. See docs/CLARIFICATIONS.md for the extractor's
     documented coverage and limitations.

Usage:
    python cli.py examples/hip_implant.json
    python cli.py < examples/hip_implant.json
    python cli.py examples/hip_implant.json --json
    python cli.py --text "A sterile, single-use hypodermic syringe."
    python cli.py --text "A sterile, single-use hypodermic syringe." --json
"""

from __future__ import annotations

import argparse
import json
import sys
import typing
from enum import Enum
from pathlib import Path

from extraction.base import ExtractionResult
from extraction.keyword_extractor import KeywordExtractor
from rules_engine.eu_mdr.engine import EUMDRClassificationEngine
from rules_engine.models import ClassificationResult, DeviceAttributes, RuleOutcome

DISCLAIMER = (
    "This is an educational/demonstration tool, not real regulatory or "
    "legal advice. Always consult a notified body / regulatory "
    "professional for an actual device classification."
)


def device_attributes_from_dict(data: dict) -> DeviceAttributes:
    """Build a DeviceAttributes instance from a plain dict (e.g. loaded
    JSON), coercing string values into the appropriate Enum types."""
    hints = typing.get_type_hints(DeviceAttributes)
    kwargs = {}
    for key, value in data.items():
        if key not in hints:
            raise ValueError(
                f"Unknown DeviceAttributes field: {key!r}. "
                f"See rules_engine/models.py for valid field names."
            )
        kwargs[key] = _coerce_value(hints[key], value)
    return DeviceAttributes(**kwargs)


def _coerce_value(field_type, value):
    if value is None:
        return None
    origin = typing.get_origin(field_type)
    if origin is typing.Union:
        non_none_args = [a for a in typing.get_args(field_type) if a is not type(None)]
        return _coerce_value(non_none_args[0], value)
    if isinstance(field_type, type) and issubclass(field_type, Enum):
        return field_type(value)
    return value


def _print_extraction_report(extraction: ExtractionResult) -> None:
    print("Extraction (from free text, via the default keyword extractor):")
    print("  Matched signals:")
    if not extraction.matched_signals:
        print("    (none - no keyword matches found in the given text)")
    else:
        for signal in extraction.matched_signals:
            print(f"    - {signal}")
    if extraction.unmatched_notes:
        print("  COULD NOT DETERMINE (verify these manually before trusting the result):")
        for note in extraction.unmatched_notes:
            print(f"    ! {note}")
    if extraction.clarifying_questions:
        print("  QUESTIONS TO RESOLVE THIS CLASSIFICATION:")
        for i, question in enumerate(extraction.clarifying_questions, start=1):
            print(f"    {i}. {question}")
    print()


def _extraction_to_dict(extraction: ExtractionResult) -> dict:
    return {
        "matched_signals": extraction.matched_signals,
        "unmatched_notes": extraction.unmatched_notes,
        "clarifying_questions": extraction.clarifying_questions,
    }


def _result_to_dict(
    device: DeviceAttributes,
    result: ClassificationResult,
    extraction: ExtractionResult | None = None,
) -> dict:
    def outcome_to_dict(o: RuleOutcome) -> dict:
        return {
            "rule_id": o.rule_id,
            "applies": o.applies,
            "device_class": o.device_class.value if o.device_class else None,
            "rationale": o.rationale,
            "source_citation": o.source_citation,
            "ambiguous": o.ambiguous,
            "ambiguous_note": o.ambiguous_note,
        }

    return {
        "device_name": device.name,
        "extraction": _extraction_to_dict(extraction) if extraction is not None else None,
        "predicted_class": result.device_class.value if result.device_class else None,
        "qualifiers": [q.value for q in result.qualifiers],
        "explanation": result.explanation,
        "triggered_rules": [outcome_to_dict(o) for o in result.triggered_rules],
        "all_rule_outcomes": [outcome_to_dict(o) for o in result.all_rule_outcomes],
        "disclaimer": DISCLAIMER,
    }


def _print_report(
    device: DeviceAttributes,
    result: ClassificationResult,
    extraction: ExtractionResult | None = None,
) -> None:
    print(f"Device: {device.name or '(unnamed)'}")
    if device.description:
        print(f"Description: {device.description}")
    print()

    if extraction is not None:
        _print_extraction_report(extraction)

    if result.device_class is None:
        print("Predicted classification: UNDETERMINED (no rule matched)")
    else:
        qualifier_str = (
            f" ({', '.join(q.value for q in result.qualifiers)})" if result.qualifiers else ""
        )
        print(f"Predicted classification: Class {result.device_class.value}{qualifier_str}")
    print()
    print(result.explanation)
    print()

    print("Triggered rules (all that applied, highest class first):")
    if not result.triggered_rules:
        print("  (none)")
    else:
        for outcome in sorted(
            result.triggered_rules, key=lambda o: o.device_class.rank, reverse=True
        ):
            print(f"  - {outcome.rule_id} -> Class {outcome.device_class.value}")
            print(f"      Why: {outcome.rationale}")
            print(f"      Source: {outcome.source_citation}")
            if outcome.ambiguous:
                print(f"      JUDGEMENT CALL FLAGGED: {outcome.ambiguous_note}")
    print()

    # Full transparency: show what every one of the 22 rules decided, not
    # just the ones that applied - so a Class I result is visibly "we
    # checked all 22 rules and only Rule 1's default applied," not a
    # silent absence of information. See result.explanation above for the
    # decisive rule(s); this is the complete audit trail behind it.
    print("Full rule-by-rule breakdown (all 22 Annex VIII rules evaluated):")
    decisive_ids = {o.rule_id for o in result.triggered_rules if o.device_class == result.device_class}
    for outcome in result.all_rule_outcomes:
        if outcome.applies and outcome.device_class is not None:
            status = "DECISIVE" if outcome.rule_id in decisive_ids else "triggered, not decisive"
            print(f"  {outcome.rule_id:<8} -> Class {outcome.device_class.value:<4} [{status}]")
        else:
            print(f"  {outcome.rule_id:<8} -> did not apply ({outcome.rationale})")
    print()
    print(DISCLAIMER)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "input",
        nargs="?",
        help="Path to a JSON file of device attributes. Omit or pass '-' to read JSON from stdin.",
    )
    input_group.add_argument(
        "--text",
        metavar="DESCRIPTION",
        help=(
            "A free-text device description to run through the default keyword "
            "extractor instead of reading structured JSON."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of a human-readable report.",
    )
    args = parser.parse_args(argv)

    extraction: ExtractionResult | None = None

    if args.text is not None:
        extraction = KeywordExtractor().extract(args.text)
        device = extraction.device
    else:
        if args.input and args.input != "-":
            raw = Path(args.input).read_text(encoding="utf-8")
        else:
            raw = sys.stdin.read()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"Invalid JSON input: {exc}", file=sys.stderr)
            return 1

        try:
            device = device_attributes_from_dict(data)
        except (ValueError, TypeError) as exc:
            print(f"Invalid device attributes: {exc}", file=sys.stderr)
            return 1

    engine = EUMDRClassificationEngine()
    result = engine.classify(device)

    if args.json:
        print(json.dumps(_result_to_dict(device, result, extraction), indent=2))
    else:
        _print_report(device, result, extraction)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
