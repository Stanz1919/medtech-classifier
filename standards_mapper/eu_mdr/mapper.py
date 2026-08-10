"""EU MDR 2017/745 standards mapper.

Evaluates all 14 GSPR categories in ``requirements.ALL_REQUIREMENTS``
against a device. Unlike ``EUMDRClassificationEngine``, there is no
precedence logic to apply here - every GSPR category is independent (a
device can need biocompatibility testing AND a software lifecycle
process AND sterilisation validation all at once), so the result is
simply every category's outcome, full stop.
"""

from __future__ import annotations

from rules_engine.models import ClassificationResult, DeviceAttributes
from standards_mapper.base import StandardsMapper, StandardsMappingResult
from standards_mapper.eu_mdr.requirements import ALL_REQUIREMENTS


class EUMDRStandardsMapper(StandardsMapper):
    """Standards mapper for Regulation (EU) 2017/745, Annex I."""

    def __init__(self) -> None:
        self._checks = [check_cls() for check_cls in ALL_REQUIREMENTS]

    def map(self, device: DeviceAttributes, classification: ClassificationResult) -> StandardsMappingResult:
        all_requirements = [check.evaluate(device, classification) for check in self._checks]
        return StandardsMappingResult(all_requirements=all_requirements)
