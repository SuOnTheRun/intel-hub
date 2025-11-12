# src/theming.py
import streamlit as st

QUIET_LUXURY_CSS = """
<style>
:root {
  --bg:#0e0f11; --panel:#15171b; --soft:#1a1d22; --ink:#e7e9ee; --muted:#9aa3ad;
  --accent:#e0c078; --accent-2:#86b4e6; --success:#6dc3a6; --warn:#e3b36f; --risk:#ef6e6e;
  --radius:18px; --shadow:0 14px 34px rgba(0,0,0,.40);
}
html, body, .stApp {background:var(--bg); color:var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;}
h1 {font-weight:800; letter-spacing:.2px; margin-bottom:.1rem;}
h2,h3 {font-weight:700; letter-spacing:.15px;}
hr {border:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent); margin:1.2rem 0;}
.block-container {max-width: 1240px; padding-top: 1.2rem;}
/* Panels */
section.main > div > div {gap: 16px;}
div[data-testid="stVerticalBlock"] > div {background: var(--panel); border-radius: var(--radius); box-shadow: var(--shadow); padding:14px 16px;}
div[data-testid="stMetric"] {background: var(--soft); border-radius: 14px; padding:.75rem 1rem; border:1px solid rgba(255,255,255,.06);}
div[data-testid="stMetricValue"] {color: var(--accent); font-weight:800;}
/* Tables */
thead tr th {background: var(--soft)!important; color: var(--ink)!important;}
tbody tr:nth-child(odd) {background: rgba(255,255,255,.02)!important;}
/* Links */
a {color: var(--accent-2); text-decoration: none;}
a:hover {text-decoration: underline;}
/* Badges */
.badge {display:inline-block; font-size:.72rem; padding:.2rem .45rem; border-radius:999px; background:rgba(255,255,255,.06); color:var(--muted); border:1px solid rgba(255,255,255,.08);}
/* Notes */
.calc-note { color: var(--muted); font-size: 0.82rem; line-height: 1.25rem; margin-top: .25rem; }
</style>
"""


def set_dark_theme() -> None:
    """Injects the quiet-luxury dark theme."""
    st.markdown(QUIET_LUXURY_CSS, unsafe_allow_html=True)

def hlabel(text: str, badge: str | None = None, badge_class: str = "") -> None:
    """Section header with optional badge."""
    if badge:
        st.markdown(f"### {text} <span class='badge {badge_class}'>{badge}</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"### {text}")
