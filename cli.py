#!/usr/bin/env python3
"""CLI harness for the EU MDR 2017/745 classification rules engine.

Phase 1 scope: takes a structured device-attribute JSON object directly -
bypassing the (not-yet-built) free-text extraction layer entirely - and
prints the predicted Annex VIII classification, which rule(s) decided it,
and why. See README.md for the DeviceAttributes field reference and
examples/ for sample input files.

Usage:
    python cli.py examples/hip_implant.json
    python cli.py < examples/hip_implant.json
    python cli.py examples/hip_implant.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
import typing
from enum import Enum
from pathlib import Path

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


def _result_to_dict(device: DeviceAttributes, result: ClassificationResult) -> dict:
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
        "predicted_class": result.device_class.value if result.device_class else None,
        "qualifiers": [q.value for q in result.qualifiers],
        "explanation": result.explanation,
        "triggered_rules": [outcome_to_dict(o) for o in result.triggered_rules],
        "all_rule_outcomes": [outcome_to_dict(o) for o in result.all_rule_outcomes],
        "disclaimer": DISCLAIMER,
    }


def _print_report(device: DeviceAttributes, result: ClassificationResult) -> None:
    print(f"Device: {device.name or '(unnamed)'}")
    if device.description:
        print(f"Description: {device.description}")
    print()

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
    print(DISCLAIMER)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a JSON file of device attributes. Omit or pass '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON instead of a human-readable report.",
    )
    args = parser.parse_args(argv)

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
        print(json.dumps(_result_to_dict(device, result), indent=2))
    else:
        _print_report(device, result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
