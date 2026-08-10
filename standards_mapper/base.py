"""Abstract interface for standards mapping: a classified device -> the
General Safety and Performance Requirements (GSPRs) it must meet, and the
standards commonly used to demonstrate conformity with each one.

Mirrors the two patterns already established in this codebase:

  - Like ``rules_engine.base``, this is jurisdiction-agnostic on purpose.
    ``StandardsMapper`` says nothing EU-specific; the EU MDR
    implementation lives in ``standards_mapper.eu_mdr``.
  - Like ``rules_engine.eu_mdr.rules``, each GSPR category is its own
    small ``GSPRRequirementCheck`` class citing the exact Annex I point
    (or Article, for the handful of universal obligations Annex I itself
    doesn't create - quality management and clinical evaluation) it
    implements. See docs/legal_sources/annex_i_general_safety_performance_requirements.txt
    and the article_*_extract.txt files alongside it for the verbatim
    text every citation in this package was checked against.

One important distinction this module is deliberately careful about:
classification (rules_engine) answers a question the regulation itself
answers deterministically - "which Annex VIII rule(s) apply" has one
legally correct answer given the facts. Standards mapping does not work
that way. Article 8 of the Regulation gives a manufacturer a presumption
of conformity with a GSPR *if* they follow a formally "harmonised
standard" (a specific, dated, Official-Journal-published list) - but
compliance can always be demonstrated by other means too, and this
module has no verified, current copy of that harmonised-standards list
to check devices against. So every standard named here is described as
"commonly used to demonstrate conformity with" a GSPR, grounded in that
standard's own well-known scope and the Annex I text it addresses - never
asserted to be *the* legally mandated standard, or asserted to currently
hold formal harmonised status. Treat every ``StandardApplicability`` as a
research starting point, not a compliance determination.

Full transparency by default, matching ``ClassificationResult``: a
``StandardsMappingResult`` always reports every GSPR category that was
checked, including the ones that don't apply and why - not just the
applicable subset.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from rules_engine.models import ClassificationResult, DeviceAttributes


@dataclass
class StandardApplicability:
    """One standard commonly used to demonstrate conformity with a GSPR.

    Attributes:
        standard_id: The standard's designation, e.g. "ISO 14971".
        title: Its official title.
        note: Any caveat specific to this device - e.g. which of several
            method-dependent parts might apply, or why this classifier
            can't narrow it further than the parent/family standard.
    """

    standard_id: str
    title: str
    note: str = ""


@dataclass
class GSPRRequirement:
    """The outcome of checking one GSPR category against a device.

    Mirrors ``RuleOutcome``'s shape on purpose: ``applies`` +
    ``rationale`` + ``source_citation`` for every category, whether or
    not it turned out to apply, so the full checklist is always visible.
    """

    requirement_id: str
    title: str
    applies: bool
    rationale: str
    source_citation: str
    standards: list[StandardApplicability] = field(default_factory=list)
    limitation_note: str = ""


@dataclass
class StandardsMappingResult:
    """The full output of mapping a device to its applicable GSPRs."""

    all_requirements: list[GSPRRequirement] = field(default_factory=list)

    @property
    def applicable_requirements(self) -> list[GSPRRequirement]:
        return [r for r in self.all_requirements if r.applies]


class GSPRRequirementCheck(ABC):
    """A single GSPR category (e.g. biocompatibility, sterility, software
    lifecycle). Implementations must be pure functions of the given
    device + classification - no I/O, no randomness, no hidden state."""

    requirement_id: str
    title: str
    source_citation: str

    @abstractmethod
    def evaluate(
        self, device: DeviceAttributes, classification: ClassificationResult
    ) -> GSPRRequirement:
        """Evaluate this GSPR category against a device and return its outcome."""
        raise NotImplementedError


class StandardsMapper(ABC):
    """Evaluates all GSPR categories for a jurisdiction against a device."""

    @abstractmethod
    def map(
        self, device: DeviceAttributes, classification: ClassificationResult
    ) -> StandardsMappingResult:
        """Return the full standards mapping for a classified device."""
        raise NotImplementedError
