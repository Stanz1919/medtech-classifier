"""Free-text -> DeviceAttributes extraction layer. Not implemented in Phase 1.

Phase 2 will add a keyword/rule-based extractor as the default, with an
optional LLM-based extractor as an upgrade path. Both will produce a
``rules_engine.models.DeviceAttributes`` instance, so the rules engine
never needs to know which extractor was used.
"""
