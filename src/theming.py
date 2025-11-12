# src/theming.py
import streamlit as st

QUIET_LUXURY_CSS = """
<style>
:root {
  --bg:#0e0f11; --panel:#15171b; --soft:#1a1d22; --ink:#e7e9ee; --muted:#9aa3ad;
  --accent:#e0c078; --accent-2:#86b4e6; --success:#6dc3a6; --warn:#e3b36f; --risk:#ef6e6e;
  --radius:16px; --shadow:0 10px 28px rgba(0,0,0,.38);
}
/* Base */
html, body, .stApp {background:var(--bg); color:var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;}
.block-container {max-width:1220px; padding-top: 1.1rem;}
h1 {font-weight:800; margin:.2rem 0 0.8rem;}
h2,h3 {font-weight:700;}
hr {border:0; height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent); margin:1rem 0;}
/* Do NOT blanket-style every block (this caused misalignment). Instead, only style known content blocks. */
[data-testid="stMetric"], [data-testid="stDataFrame"], [data-testid="stMarkdownContainer"], [data-testid="stVerticalBlock"] > div:has(> div[data-testid="stChart"]) {
  background: var(--panel); border-radius: var(--radius); box-shadow: var(--shadow); padding: 14px 16px; border:1px solid rgba(255,255,255,.06);
}
[data-testid="stMetric"] { background: var(--soft); }
div[data-testid="stMetricValue"] { color: var(--accent); font-weight:800; }
/* Tables */
thead tr th {background: var(--soft)!important; color: var(--ink)!important;}
tbody tr:nth-child(odd) {background: rgba(255,255,255,.02)!important;}
/* Links */
a {color: var(--accent-2); text-decoration: none;} a:hover {text-decoration: underline;}
/* Badges / Notes */
.badge {display:inline-block; font-size:.72rem; padding:.2rem .45rem; border-radius:999px; background:rgba(255,255,255,.06); color:var(--muted); border:1px solid rgba(255,255,255,.08);}
.calc-note { color: var(--muted); font-size:.82rem; line-height:1.25rem; margin-top:.25rem; }
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
