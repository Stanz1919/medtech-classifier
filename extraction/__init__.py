"""Free-text -> DeviceAttributes extraction layer.

``KeywordExtractor`` (in ``keyword_extractor.py``) is the default,
deterministic extractor per the project brief - keyword/rule-based is
the lead path, not a fallback. An LLM-based extractor is an optional
future upgrade that would implement the same ``base.Extractor``
interface.
"""

from extraction.base import Extractor, ExtractionResult
from extraction.keyword_extractor import KeywordExtractor

__all__ = ["Extractor", "ExtractionResult", "KeywordExtractor"]
