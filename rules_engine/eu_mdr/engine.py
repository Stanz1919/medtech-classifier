"""EU MDR 2017/745 classification engine.

Evaluates all 22 Annex VIII rules against a device and applies the
cross-rule precedence mandated by Annex VIII Chapter II, point 3.5: "If
several rules... apply to the same device based on the device's intended
purpose, the strictest rule and sub-rule resulting in the higher
classification shall apply."

Also applies Article 52(7): Class I devices that are placed on the
market sterile, have a measuring function, or are reusable surgical
instruments get the informal "Is"/"Im"/"Ir" qualifiers noted alongside
the base class. These qualifiers are computed independently of Annex
VIII rule evaluation - they do not affect precedence and never change
the base class.
"""

from __future__ import annotations

from rules_engine.base import ClassificationEngine
from rules_engine.eu_mdr.rules import ALL_RULES
from rules_engine.models import (
    ClassificationResult,
    ClassQualifier,
    DeviceAttributes,
    DeviceClass,
    highest,
)


class EUMDRClassificationEngine(ClassificationEngine):
    """Classification engine for Regulation (EU) 2017/745, Annex VIII."""

    def __init__(self) -> None:
        self._rules = [rule_cls() for rule_cls in ALL_RULES]

    def classify(self, device: DeviceAttributes) -> ClassificationResult:
        all_outcomes = [rule.evaluate(device) for rule in self._rules]
        triggered = [o for o in all_outcomes if o.applies and o.device_class is not None]

        final_class = highest(*(o.device_class for o in triggered))

        qualifiers: list[ClassQualifier] = []
        if final_class == DeviceClass.I:
            if device.placed_on_market_sterile:
                qualifiers.append(ClassQualifier.STERILE)
            if device.has_measuring_function:
                qualifiers.append(ClassQualifier.MEASURING_FUNCTION)
            if device.is_reusable_surgical_instrument:
                qualifiers.append(ClassQualifier.REUSABLE_SURGICAL_INSTRUMENT)

        explanation = self._build_explanation(final_class, qualifiers, triggered)

        return ClassificationResult(
            device_class=final_class,
            qualifiers=qualifiers,
            triggered_rules=triggered,
            all_rule_outcomes=all_outcomes,
            explanation=explanation,
        )

    @staticmethod
    def _build_explanation(
        final_class: DeviceClass | None,
        qualifiers: list[ClassQualifier],
        triggered: list,
    ) -> str:
        if final_class is None:
            return (
                "No Annex VIII rule matched the given attributes, so no "
                "classification could be determined. This usually means the "
                "device attributes are incomplete - Rule 1 (non-invasive -> "
                "Class I) or Rule 13 (other active devices -> Class I) should "
                "catch most fully-specified devices."
            )

        deciding = [o for o in triggered if o.device_class == final_class]
        deciding_ids = ", ".join(o.rule_id for o in deciding)
        qualifier_str = f" ({', '.join(q.value for q in qualifiers)})" if qualifiers else ""

        lines = [
            f"Predicted classification: Class {final_class.value}{qualifier_str}.",
            f"Highest-ranked triggered rule(s): {deciding_ids}.",
            "Per Annex VIII Chapter II, point 3.5, when multiple rules apply "
            "the rule producing the highest classification governs.",
        ]
        if len(triggered) > len(deciding):
            other_ids = ", ".join(
                f"{o.rule_id} -> Class {o.device_class.value}" for o in triggered if o.device_class != final_class
            )
            lines.append(f"Other triggered rules (lower classification, not decisive): {other_ids}.")
        return " ".join(lines)
