"""Deterministic, auditable classification rules engine.

Jurisdiction-agnostic core (``base``, ``models``) plus jurisdiction-
specific implementations as subpackages. Currently only ``eu_mdr``
(Regulation (EU) 2017/745, Annex VIII) exists; a future ``uk_mdr``
package would implement the same ``ClassificationEngine`` /
``ClassificationRule`` interfaces from ``rules_engine.base``.
"""
