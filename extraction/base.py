"""Abstract interface for extraction: free text -> DeviceAttributes.

Kept deliberately method-agnostic, mirroring the ``rules_engine.base``
pattern: this module says nothing about *how* extraction happens.
``keyword_extractor.KeywordExtractor`` is the default, deterministic
implementation (per the project brief: keyword/rule-based is the lead
path, not an LLM). A future LLM-based extractor would implement this
same ``Extractor`` interface, so the CLI (and later the Streamlit UI)
can depend on ``Extractor`` without caring which implementation produced
a given ``DeviceAttributes`` instance.

Extraction is fundamentally different from classification in one
important way: the rules engine is deterministic and, given a correct
input, provably correct (it's tested against real regulatory examples).
Extraction from free text is inherently lossy and ambiguous - the same
sentence can support more than one reasonable reading. ``ExtractionResult``
exists to make that uncertainty visible rather than hiding it behind a
confident-looking ``DeviceAttributes`` object: every extractor is
expected to report *which* text triggered *which* field, and to leave
fields it couldn't confidently determine at their dataclass defaults
rather than guess.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from rules_engine.models import DeviceAttributes


@dataclass
class ExtractionResult:
    """The result of extracting structured attributes from free text.

    Attributes:
        device: The populated (partially, usually) DeviceAttributes.
        matched_signals: Human-readable log of what text triggered what
            field, e.g. "invasiveness = SURGICALLY_INVASIVE (matched
            'implant')". Intended for CLI/UI display so a user can see
            *why* the extractor concluded what it did, not just the
            result - the same transparency principle the rules engine
            applies via RuleOutcome.rationale.
        unmatched_notes: Human-readable notes about fields the extractor
            deliberately left at their default because it found no
            reliable signal for them (as opposed to fields it never
            attempts - see each extractor's own documented coverage).
        clarifying_questions: Specific, answerable questions the user
            should resolve to firm up a classification that currently
            rests on a genuine judgement call rather than a clear textual
            signal (e.g. software severity - see
            docs/CLARIFICATIONS_RULE_11.md). Distinct from
            unmatched_notes: a note says "we don't know X"; a clarifying
            question says "tell us X, or take this exact question to a
            regulatory professional" and names what each answer would
            change about the result.
    """

    device: DeviceAttributes
    matched_signals: list[str] = field(default_factory=list)
    unmatched_notes: list[str] = field(default_factory=list)
    clarifying_questions: list[str] = field(default_factory=list)


class Extractor(ABC):
    """Turns a free-text device description into a DeviceAttributes."""

    @abstractmethod
    def extract(self, text: str) -> ExtractionResult:
        """Extract structured attributes from a free-text description."""
        raise NotImplementedError
