"""Shared visual theme for the UI - "Direction B" from the Carbon-inspired
comparison the user picked: the project's existing dark base, restyled
with IBM Carbon's structural discipline (one blue accent, square corners
everywhere, hairline borders instead of shadows) rather than Carbon's
own light canvas. Layered on top of the native Streamlit components that
already re-theme correctly on their own (st.badge, st.metric,
st.dataframe - see ui/render.py's module docstring for why those were
chosen deliberately in Phase 4).

.streamlit/config.toml sets the actual default theme (base="dark",
primaryColor matching the accent below) that essentially every viewer
sees. The CSS injected here is for the custom HTML sections config.toml
alone can't reach (hero banner, feature cards, step markers, stat strip,
in-page nav, scroll-reveal, scroll progress bar) - it deliberately
commits to the dark palette unconditionally rather than branching on a
`prefers-color-scheme` media query, for the same reason documented at
length in git history: that query reflects the OS/browser's preference,
not Streamlit's own active theme, and verifying this UI live caught the
two disagreeing in practice. Every native Streamlit widget re-themes
correctly on its own regardless.

Two Streamlit-specific technical notes worth knowing before touching
this file:

1. Raw <script> tags injected via st.markdown(unsafe_allow_html=True)
   are silently stripped - verified empirically (a script that should
   have overwritten a div's text simply never ran). The reliable path
   for real JS (scroll-reveal, the progress bar, count-up stats) is
   st.components.v1.html(), which renders in an iframe Streamlit serves
   same-origin - confirmed live that the iframe's script can reach
   window.parent.document and manipulate the real page. inject_scroll_effects()
   below is the one place that happens; every other visual effect here
   is CSS-only.
2. [data-testid="stBaseButton-primary"] is real, verified markup (read
   directly off a running instance), not a guessed class name - safe to
   target for the square-corner override on primary buttons, unlike the
   auto-generated st-emotion-cache-* hash classes, which change per build.

Call ``inject_css()`` once near the top of every page script (safe to
call from more than one page - unlike ``st.set_page_config()``, which
must only ever be called once and lives solely in ``ui/app.py``, the
router). Call ``inject_scroll_effects()`` once per page that uses
``mt-reveal``/``data-count-to`` markup or wants the progress bar - today
that's only ui/pages/home.py; the classify/results page intentionally
does not use scroll-gated reveals (see its own module docstring for why
hiding functional output behind scroll position would be bad UX there).
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

_CSS = """
<style>
:root {
    --mt-bg-elevated: #131C31;
    --mt-border: #223049;
    --mt-text: #E2E8F0;
    --mt-text-muted: #93A4BE;
    --mt-text-subtle: #64748B;
    --mt-accent: #4589FF;
    --mt-accent-strong: #6EA8FF;
    --mt-accent-soft: rgba(69, 137, 255, 0.14);
    --mt-radius: 0px;
}

* { scrollbar-color: var(--mt-border) transparent; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--mt-border); border: 2px solid #0B1220; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: var(--mt-text-subtle); }

html { scroll-behavior: smooth; }
@media (prefers-reduced-motion: reduce) {
    html { scroll-behavior: auto; }
}

/* Square off Streamlit's own primary button to match the flat-geometry
   discipline everywhere else - see module docstring note 2. */
[data-testid="stBaseButton-primary"] {
    border-radius: var(--mt-radius) !important;
}

:focus-visible {
    outline: 2px solid var(--mt-accent) !important;
    outline-offset: 2px !important;
}

/* Thin top progress bar - the div lives here (plain HTML, always
   allowed); inject_scroll_effects() drives its width on scroll. */
#mt-scroll-progress {
    position: fixed;
    top: 0;
    left: 0;
    height: 3px;
    width: 0%;
    background: var(--mt-accent);
    z-index: 999999;
    pointer-events: none;
}

/* Hero banner (home page) */
.mt-hero {
    padding: 2.75rem 2.5rem;
    border-radius: var(--mt-radius);
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
    border-radius: var(--mt-radius);
    padding: 1.4rem 1.5rem;
    height: 100%;
    transition: border-color 0.2s ease, background-color 0.2s ease;
}
.mt-card:hover {
    border-color: var(--mt-accent);
    background: #16213D;
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
    border-radius: var(--mt-radius);
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

/* Stat strip - real numbers, count-up driven by inject_scroll_effects() */
.mt-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 1px;
    background: var(--mt-border);
    border: 1px solid var(--mt-border);
    margin-bottom: 1.75rem;
}
.mt-stat {
    flex: 1 1 140px;
    background: var(--mt-bg-elevated);
    padding: 1.1rem 1.3rem;
}
.mt-stat-num {
    font-size: 1.9rem;
    font-weight: 800;
    color: var(--mt-accent);
    letter-spacing: -0.01em;
    font-variant-numeric: tabular-nums;
}
.mt-stat-label {
    font-size: 0.78rem;
    color: var(--mt-text-muted);
    margin-top: 0.15rem;
}

/* In-page anchor nav */
.mt-subnav {
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    gap: 1.5rem;
    padding: 0.75rem 0.25rem;
    margin-bottom: 1.5rem;
    background: rgba(11, 18, 32, 0.92);
    backdrop-filter: blur(6px);
    border-bottom: 1px solid var(--mt-border);
}
.mt-subnav a {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--mt-text-muted);
    text-decoration: none;
    scroll-margin-top: 4.5rem;
}
.mt-subnav a:hover { color: var(--mt-accent); }

/* Scroll-reveal - see inject_scroll_effects(). Normally .mt-revealed is
   added by IntersectionObserver when JS runs. But verified live (this
   exact document.hidden/non-composited case, not a hypothetical) that
   IntersectionObserver callbacks can simply never fire in a browsing
   context that isn't actively compositing frames - and the JS-side
   setTimeout fallback in inject_scroll_effects() only helps if the
   script ran at all. So there are two independent, redundant
   fallbacks, not one: the JS timeout below, and this animation, which
   needs no JavaScript whatsoever and guarantees content is visible
   within a few seconds even in a total-script-failure scenario. A
   permanently-invisible section would be a far worse failure mode than
   a missed fade-in animation.
*/
.mt-reveal {
    opacity: 0;
    transform: translateY(16px);
    transition: opacity 0.6s ease, transform 0.6s ease;
    animation: mt-reveal-fallback 0.01s linear 3s forwards;
}
.mt-reveal.mt-revealed {
    opacity: 1;
    transform: translateY(0);
}
@keyframes mt-reveal-fallback {
    to { opacity: 1; transform: none; }
}
@media (prefers-reduced-motion: reduce) {
    .mt-reveal { opacity: 1; transform: none; transition: none; animation: none; }
}
</style>
"""

_SCROLL_EFFECTS_JS = """
<script>
(function () {
    var win = window.parent;
    var doc = win.document;
    var reduceMotion = win.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // --- Scroll-reveal ---
    // Belt-and-suspenders against a real, observed failure mode, not a
    // hypothetical: verified live that IntersectionObserver callbacks
    // can simply never fire in a browsing context that isn't actively
    // compositing frames (document.hidden === true). A setTimeout
    // fallback force-reveals everything regardless - a missed fade-in
    // is a trivial cosmetic loss, a permanently invisible section is
    // not. The CSS-only @keyframes fallback in the stylesheet is the
    // second, independent layer for the case where this script doesn't
    // run at all.
    var revealEls = doc.querySelectorAll('.mt-reveal:not(.mt-revealed)');
    if (reduceMotion) {
        revealEls.forEach(function (el) { el.classList.add('mt-revealed'); });
    } else if (revealEls.length) {
        var io = new win.IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('mt-revealed');
                    io.unobserve(entry.target);
                }
            });
        }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
        revealEls.forEach(function (el) { io.observe(el); });
        win.setTimeout(function () {
            revealEls.forEach(function (el) { el.classList.add('mt-revealed'); });
            io.disconnect();
        }, 1800);
    }

    // --- Count-up stats ---
    function animateCount(el) {
        var target = parseInt(el.getAttribute('data-count-to'), 10);
        var suffix = el.getAttribute('data-count-suffix') || '';
        if (reduceMotion || isNaN(target)) {
            el.textContent = target + suffix;
            return;
        }
        var duration = 1100;
        var start = win.performance.now();
        // requestAnimationFrame is paint-tied, same as IntersectionObserver -
        // verified live that its callback can also simply never fire in a
        // non-compositing context, which would otherwise leave the count
        // stuck at 0 forever (not delayed - genuinely never progressing,
        // since tick() only re-schedules itself via further rAF calls).
        // win.setTimeout is a plain timer, confirmed reliable regardless,
        // so it - not rAF - is what guarantees the correct final number;
        // the rAF path is purely a nicer-looking animation on top when the
        // browser is actually compositing.
        win.setTimeout(function () { el.textContent = target + suffix; }, duration + 150);
        function tick(now) {
            var progress = Math.min((now - start) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = Math.round(eased * target) + suffix;
            if (progress < 1) { win.requestAnimationFrame(tick); }
        }
        win.requestAnimationFrame(tick);
    }
    function finishCount(el) {
        if (el.hasAttribute('data-counted')) { return; }
        el.setAttribute('data-counted', 'true');
        animateCount(el);
    }
    var countEls = doc.querySelectorAll('[data-count-to]:not([data-counted])');
    if (countEls.length) {
        var countIo = new win.IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) { finishCount(entry.target); countIo.unobserve(entry.target); }
            });
        }, { threshold: 0.5 });
        countEls.forEach(function (el) { countIo.observe(el); });
        win.setTimeout(function () {
            countEls.forEach(finishCount);
            countIo.disconnect();
        }, 1800);
    }

    // --- Scroll progress bar ---
    // Streamlit's page does not scroll window/body - the actual
    // scrollable element is [data-testid="stMain"] (confirmed by
    // inspecting a running instance: window.scrollY stayed 0 while the
    // page visibly scrolled). Bind to that, not the window.
    var bar = doc.getElementById('mt-scroll-progress');
    var scrollHost = doc.querySelector('[data-testid="stMain"]');
    if (bar && scrollHost) {
        function updateBar() {
            var scrollTop = scrollHost.scrollTop;
            var trackHeight = scrollHost.scrollHeight - scrollHost.clientHeight;
            var pct = trackHeight > 0 ? Math.min(100, (scrollTop / trackHeight) * 100) : 0;
            bar.style.width = pct + '%';
        }
        if (!win.__mtScrollBarBound) {
            win.__mtScrollBarBound = true;
            scrollHost.addEventListener('scroll', updateBar, { passive: true });
        }
        updateBar();
    }
})();
</script>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div id="mt-scroll-progress"></div>', unsafe_allow_html=True)


def inject_scroll_effects() -> None:
    """Wires up scroll-reveal (.mt-reveal), count-up ([data-count-to]),
    and the #mt-scroll-progress bar against the real page - see the
    module docstring for why this needs components.html rather than a
    plain injected <script>. Zero visible footprint (height=0 iframe).

    This logs a "replace with st.iframe" deprecation notice on the
    installed Streamlit version - left as-is deliberately: st.iframe
    takes a src (URL/file path), not an inline HTML/JS string, so it
    isn't a like-for-like replacement for what this needs, and
    components.html is verified working (checked directly against a
    running instance) on the version this project targets.
    """
    components.html(_SCROLL_EFFECTS_JS, height=0)
