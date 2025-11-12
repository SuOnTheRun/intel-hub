# src/theming.py
import streamlit as st

QUIET_LUXURY_CSS = """
<style>
:root {
  --bg:#0d0f12; --panel:#15181c; --soft:#1a1e23; --ink:#e7e9ee; --muted:#9aa3ad;
  --accent:#e0c078; --accent-2:#86b4e6; --success:#68c3a7; --warn:#e3b36f; --risk:#ef6e6e;
  --r:8px; --shadow:0 8px 22px rgba(0,0,0,.30);
}
/* Base */
html, body, .stApp {background:var(--bg); color:var(--ink); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;}
.block-container {max-width:1200px; padding-top: 1.0rem;}
h1 {font-weight:800; margin:.2rem 0 .8rem;}
h2,h3 {font-weight:700;}
hr {border:0; height:1px; background:linear-gradient(90deg,transparent,rgba(255,255,255,.08),transparent); margin:0.8rem 0;}

/* Executive-minimal cards: small radius, subtle borders, less shadow */
.card, [data-testid="stDataFrame"], [data-testid="stMetric"], .chart-card, .note-card {
  background: var(--panel); border-radius: var(--r); border:1px solid rgba(255,255,255,.07); box-shadow: var(--shadow);
  padding: 12px 14px;
}
/* IMPORTANT: do NOT style all Markdown containers as cards */

[data-testid="stMetric"] { background: var(--soft); }
div[data-testid="stMetricValue"] { color: var(--accent); font-weight:800; }

/* Remove “bubble” feel */
.sidebar .block-container, .stSidebar .block-container { padding: .5rem .5rem 1rem; }
.stSidebar [data-testid="stRadio"] { background: var(--panel); border:1px solid rgba(255,255,255,.07); border-radius: var(--r); padding:10px 12px; box-shadow: var(--shadow); }
.stSidebar [data-testid="stHeader"] { background: transparent; border:0; box-shadow:none; }

/* Tables */
thead tr th {background: var(--soft)!important; color: var(--ink)!important;}
tbody tr:nth-child(odd) {background: rgba(255,255,255,.02)!important;}

/* Links */
a {color: var(--accent-2); text-decoration: none;} a:hover {text-decoration: underline;}

/* Notes */
.calc-note { color: var(--muted); font-size:.85rem; line-height:1.25rem; margin-top:.25rem; }
.small { font-size:.86rem; color: var(--muted); }
.section-title { margin-bottom:.2rem; }
.section-head { font-weight:700; margin:.1rem 0 .4rem; letter-spacing:.2px; }
.section-head:after {
  content:""; display:block; height:1px; margin-top:6px;
  background: linear-gradient(90deg, var(--accent) 0%, rgba(255,255,255,.12) 40%, transparent 80%);
  opacity:.55;
}

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
