# src/theming.py
import streamlit as st

QUIET_LUXURY_CSS = """
<style>
:root {
  --bg:#0f1113; --panel:#171a1d; --soft:#1c2024; --ink:#e4e6ea; --muted:#a8b0ba;
  --accent:#e0c078; --accent-2:#7fb0e0; --success:#69c1a3; --warn:#e2b16b; --risk:#f06d6d;
  --radius:16px; --shadow:0 10px 30px rgba(0,0,0,.35);
}
html, body, .stApp {background:var(--bg); color:var(--ink); font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";}
h1,h2,h3,h4 {color:var(--ink); letter-spacing:.2px;}
hr {border:0;height:1px;background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent);}
.block-container {padding-top: 2rem; max-width: 1280px;}
/* Panels */
div[data-testid="stVerticalBlock"] > div {background: var(--panel); border-radius: var(--radius); box-shadow: var(--shadow);}
div[data-testid="stMetric"] {background: var(--soft); border-radius: 14px; padding:.75rem 1rem; border:1px solid rgba(255,255,255,.06);}
div[data-testid="stMetricValue"] {color: var(--accent); font-weight:700;}
/* Tables */
thead tr th {background: var(--soft)!important; color: var(--ink)!important;}
tbody tr:nth-child(odd) {background: rgba(255,255,255,.02)!important;}
/* Links */
a {color: var(--accent-2); text-decoration: none;}
a:hover {text-decoration: underline;}
/* Badges */
.badge {display:inline-block; font-size:.72rem; padding:.2rem .45rem; border-radius:999px; background:rgba(255,255,255,.06); color:var(--muted); border:1px solid rgba(255,255,255,.08);}
.badge.risk {background: rgba(240,109,109,.12); border-color: rgba(240,109,109,.28); color:#f3b3b3;}
.badge.ok {background: rgba(105,193,163,.12); border-color: rgba(105,193,163,.28); color:#b6e6d6;}
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
