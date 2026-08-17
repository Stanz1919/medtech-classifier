"""Shared visual theme for the UI - a dark, clinical "medtech product
site" look, layered on top of the native Streamlit components that
already re-theme correctly on their own (st.badge, st.metric,
st.dataframe - see ui/render.py's module docstring for why those were
chosen deliberately in Phase 4).

.streamlit/config.toml sets the actual default theme (base="dark") that
essentially every viewer sees. The CSS injected here is for the custom
HTML sections config.toml alone can't reach (hero banner, feature cards,
step markers) - it deliberately commits to the same dark palette
unconditionally, rather than branching on a `prefers-color-scheme` media
query. That query reflects the OS/browser's preference, not Streamlit's
own active theme - verified live (via javascript_tool against a running
instance) that the two disagree in practice: a browser reporting no
`prefers-color-scheme: dark` still correctly renders Streamlit's own
dark-themed chrome (config.toml wins), which made an earlier
light-media-query fallback here render wrong by default, not just in
some rare edge case. Every native Streamlit widget (st.badge, st.metric,
st.dataframe - see ui/render.py's module docstring) re-themes correctly
on its own regardless, so the one accepted trade-off is purely cosmetic:
these specific custom-HTML sections would look dark-on-light if a viewer
manually overrides Streamlit's own theme switcher to light - everything
functional stays correct either way.

Call ``inject_css()`` once near the top of every page script (safe to
call from more than one page - unlike ``st.set_page_config()``, which
must only ever be called once and lives solely in ``ui/app.py``, the
router).
"""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
:root {
    --mt-bg-elevated: #131C31;
    --mt-border: #223049;
    --mt-text: #E2E8F0;
    --mt-text-muted: #93A4BE;
    --mt-accent: #2DD4BF;
    --mt-accent-strong: #14B8A6;
    --mt-accent-soft: rgba(45, 212, 191, 0.12);
}

/* Hero banner (home page) */
.mt-hero {
    padding: 2.75rem 2.5rem;
    border-radius: 18px;
    background: linear-gradient(135deg, var(--mt-bg-elevated) 0%, var(--mt-accent-soft) 150%);
    border: 1px solid var(--mt-border);
    margin-bottom: 1.75rem;
}
.mt-hero h1 {
    font-size: 2.6rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.15;
    margin: 0 0 0.6rem 0;
    color: var(--mt-text);
}
.mt-hero .mt-tagline {
    font-size: 1.1rem;
    color: var(--mt-text-muted);
    max-width: 680px;
    line-height: 1.55;
    margin: 0;
}
.mt-accent { color: var(--mt-accent); }
.mt-eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--mt-accent);
    margin-bottom: 0.75rem;
}

/* Feature / step cards */
.mt-card {
    background: var(--mt-bg-elevated);
    border: 1px solid var(--mt-border);
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    height: 100%;
}
.mt-card h3 {
    font-size: 1.02rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    color: var(--mt-text);
}
.mt-card p {
    color: var(--mt-text-muted);
    font-size: 0.9rem;
    line-height: 1.55;
    margin: 0;
}
.mt-step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: var(--mt-accent-soft);
    color: var(--mt-accent);
    font-weight: 700;
    font-size: 0.85rem;
    margin-bottom: 0.7rem;
}

/* Section headings used outside st.header, for tighter control */
.mt-section-title {
    font-size: 1.5rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: var(--mt-text);
    margin: 0.25rem 0 1rem 0;
}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
