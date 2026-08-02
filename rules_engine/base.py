"""Abstract interfaces for classification rules and engines.

Kept jurisdiction-agnostic on purpose: ``ClassificationRule`` and
``ClassificationEngine`` say nothing EU-specific. The EU MDR
implementation lives in ``rules_engine.eu_mdr``. A future UK
MDR/UKCA engine (Phase 2 stretch goal, not built yet) would implement
these same two interfaces, so callers (CLI, and later the Streamlit UI)
can depend on ``ClassificationEngine`` rather than a concrete
jurisdiction's engine.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from rules_engine.models import ClassificationResult, DeviceAttributes, RuleOutcome


class ClassificationRule(ABC):
    """A single classification rule (e.g. one Annex VIII rule).

    Implementations must be pure functions of the input
    ``DeviceAttributes`` - no I/O, no randomness, no hidden state - so
    that the same input always produces the same output.
    """

    rule_id: str
    source_citation: str

    @abstractmethod
    def evaluate(self, device: DeviceAttributes) -> RuleOutcome:
        """Evaluate this rule against a device and return its outcome."""
        raise NotImplementedError


class ClassificationEngine(ABC):
    """Evaluates all rules for a jurisdiction and applies precedence."""

    @abstractmethod
    def classify(self, device: DeviceAttributes) -> ClassificationResult:
        """Return the final classification for a device."""
        raise NotImplementedError
