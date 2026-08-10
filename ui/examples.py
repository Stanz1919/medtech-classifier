"""Curated demo data for the UI - deliberately kept free of any Streamlit
import or side effect.

``ui/app.py`` is a real Streamlit script: importing it directly (as
opposed to running it via ``streamlit run`` or ``AppTest.from_file``,
which execute it inside a proper script-run context) executes every
top-level statement, including the interactive flow that depends on
``st.session_state`` - which behaves unpredictably outside a real
session and will crash. Keeping the example data here, with no
Streamlit dependency, means both ``ui/app.py`` and ``tests/test_ui.py``
can import it plainly without ever triggering that.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

JSON_EXAMPLES: dict[str, Path] = {
    p.stem.replace("_", " ").title(): p for p in sorted((REPO_ROOT / "examples").glob("*.json"))
}

# Curated free-text examples spanning the full risk ladder and the
# extractor's most distinctive documented behaviour (Rule 6/8 routing
# fixes, the clarifying-questions design for software severity) - every
# string below is taken verbatim from tests/test_extraction_known_devices.py
# and tests/test_cli.py, so the demo can never show a surprising result.
TEXT_EXAMPLES: dict[str, str] = {
    "Hypodermic syringe (Class IIa)": (
        "A sterile, single-use hypodermic syringe used to inject medicinal products under the skin."
    ),
    "Hip replacement implant (Class III)": (
        "A titanium hip replacement implant intended for permanent placement in the joint."
    ),
    "Cardiac pacemaker (Class III)": ("A cardiac pacemaker implanted permanently to regulate heart rhythm."),
    "Drug-eluting coronary stent (Class III)": (
        "A drug-eluting stent implanted in direct contact with the heart."
    ),
    "Gauze wound dressing (Class I)": (
        "A gauze dressing that acts as a mechanical barrier and absorbs exudate from a wound."
    ),
    "Reusable surgical scissors (Class I, via Rule 6)": (
        "A reusable surgical instrument used briefly during a single procedure to cut tissue."
    ),
    "Dental filling (Class IIa, via Rule 8)": (
        "A composite dental filling material placed within the tooth to restore a cavity."
    ),
    "Heartbeat monitoring app (clarifying questions)": (
        "A mobile app that analyses a patient heartbeat, detects abnormalities, and informs a physician."
    ),
}
