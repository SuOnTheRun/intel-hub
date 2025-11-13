# src/theming.py
from __future__ import annotations
import streamlit as st

_LIGHT_CSS = """
<style>
:root{
  --bg:#f7f7f8;
  --panel:#ffffff;
  --ink:#0f172a;
  --muted:#64748b;
  --border:#e6e7eb;
  --accent:#1f6feb;        /* soft blue accent */
  --accent-2:#f0f7ff;      /* pale blue fill */
  --success:#0f766e;
  --warn:#b45309;
}

html, body, .stApp { background: var(--bg) !important; color: var(--ink); }
section[data-testid="stSidebar"] { background: #fafafa !important; border-right:1px solid var(--border); }

.block-container { padding-top: 2rem; }

h1, h2, h3, h4 { color: var(--ink); letter-spacing: .2px; }
h1 { font-weight: 800; }
.section-title { margin: .25rem 0 1rem 0; font-weight: 750; }

.stMetric { background: var(--panel); border: 1px solid var(--border);
  border-radius: 14px; padding: 10px 14px; box-shadow: 0 1px 2px rgba(16,24,40,.05);
}
.stMetric label, .stMetric [data-testid="stMetricLabel"] { color: var(--muted) !important; font-weight: 600; }
.stMetric span { color: var(--ink) !important; font-weight: 800 !important; }

.card, .note-card, .chart-card {
  background: var(--panel); border:1px solid var(--border); border-radius:16px;
  padding:14px 16px; margin: 6px 0 14px 0; box-shadow: 0 1px 2px rgba(16,24,40,.05);
}
.chart-card { padding-top: 8px; }
.note-card { background: #fff; }

.calc-note, .small, .stCaption { color: var(--muted) !important; font-size: .85rem; }
.calc-note { margin-top: 6px; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

[data-testid="stTable"] table, .stDataFrame { border-radius: 10px; border:1px solid var(--border); }
[data-testid="stTable"] thead tr th, .stDataFrame thead tr th { background: #fafcff; color: #334155; }

hr { border: none; height:1px; background: var(--border); margin: 20px 0; }

.badge { background: var(--accent-2); color: var(--accent); padding: 2px 8px; border-radius: 999px; font-weight: 600; }
</style>
"""

def set_dark_theme():
    """Kept for compatibility; we now prefer light."""
    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)

def set_light_theme():
    st.markdown(_LIGHT_CSS, unsafe_allow_html=True)
