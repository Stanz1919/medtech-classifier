"""Streamlit UI for the MedTech Device Regulatory Classifier.

``app.py`` is the entry point (``streamlit run ui/app.py``); ``render.py``
holds the display helpers it calls. A sibling front-end to ``cli.py`` -
both depend only on ``rules_engine``, ``extraction`` and
``standards_mapper``, and know nothing about each other.
"""
