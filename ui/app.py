"""Router entry point for the MedTech Device Regulatory Classifier UI.

Run locally:
    streamlit run ui/app.py

This file only wires up navigation (st.set_page_config + st.navigation)
between the two pages - ui/pages/home.py (what this is, why, how it
works) and ui/pages/classify.py (the tool itself). It contains no
classification logic of its own; see ui/pages/classify.py's module
docstring for that boundary.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="MedTech Device Regulatory Classifier",
    page_icon="⚕️",
    layout="wide",
)

home_page = st.Page("pages/home.py", title="Home", icon="⚕️", default=True)
classify_page = st.Page("pages/classify.py", title="Classify", icon="🩺")

# position="top" was tried first (a top nav bar reads more like a real
# site than a sidebar) but turned out to be genuinely broken in
# practice, not just untested: with exactly these two pages, Streamlit's
# top-nav renders only a dead, permanently-hidden "1 more" overflow
# button (verified by inspecting the live DOM - data-testid="stTopNavSection",
# aria-hidden="true", pointer-events: none - with zero actual page links
# anywhere on the page) and offers no way to navigate at all. AppTest
# can't catch this class of bug - it simulates the Python-side script,
# not the real frontend rendering. "sidebar" is Streamlit's original,
# far more battle-tested multipage nav position and works correctly.
nav = st.navigation([home_page, classify_page], position="sidebar")
nav.run()
