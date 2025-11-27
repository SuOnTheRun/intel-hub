# src/theming.py
from __future__ import annotations
import streamlit as st


def set_dark_theme() -> None:
    """
    Global 'white luxury control hub' theme.

    Note: function name kept as set_dark_theme() so other modules
    don't need to change their imports.
    """
    st.set_page_config(
        page_title="Blis Intelligence Hub — US",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    css = """
    <style>
    /* ---------- Base layout ---------- */
    .stApp {
        background: #f5f5f7;  /* soft off-white */
        color: #111827;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", sans-serif;
    }

    /* widen main content */
    .main .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    /* ---------- Sidebar / navigation ---------- */
    section[data-testid="stSidebar"] {
        background: #f3f4f6;
        border-right: 1px solid #e5e7eb;
    }

    section[data-testid="stSidebar"] .css-1d391kg,  /* older streamlit */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem;
    }

    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: .12em;
        color: #6b7280;
        font-weight: 600;
    }

    /* ---------- Typography ---------- */
    h1 {
        font-size: 1.9rem !important;
        letter-spacing: .03em;
        font-weight: 650 !important;
        color: #111827;
        margin-bottom: 0.4rem;
    }

    .section-title {
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: .11em;
        color: #4b5563;
        font-weight: 600;
        margin: 0 0 0.35rem 0;
    }

    .small {
        font-size: 0.78rem;
        color: #6b7280;
    }

    .calc-note {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 0.15rem;
    }

    /* remove odd grey "header boxes" */
    h3 {
        background: transparent !important;
        padding: 0 !important;
        margin-top: 0.5rem;
    }

    /* ---------- Cards & panels ---------- */
    .card,
    .chart-card,
    .note-card {
        background: #ffffff;
        border-radius: 16px;
        border: 1px solid #e5e7eb;
        box-shadow:
            0 18px 45px rgba(15, 23, 42, 0.04),
            0 0 1px rgba(15, 23, 42, 0.08);
        padding: 1rem 1.25rem;
        margin-top: 0.75rem;
    }

    .chart-card {
        padding-top: 0.9rem;
        padding-bottom: 0.9rem;
    }

    .note-card {
        padding-top: 0.7rem;
        padding-bottom: 0.7rem;
    }

    .card ul {
        padding-left: 1.1rem;
        margin-bottom: 0.2rem;
    }

    .card li {
        margin-bottom: 0.12rem;
        line-height: 1.35;
        font-size: 0.9rem;
    }

    /* ---------- Metrics row ---------- */
    [data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 14px;
        border: 1px solid #e5e7eb;
        padding: 0.65rem 0.75rem;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
    }

    [data-testid="stMetric"] label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: .14em;
        color: #6b7280;
        font-weight: 600;
    }

    [data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.3rem;
        font-weight: 650;
        color: #111827;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.8rem;
    }

    /* accent for positive signals (subtle mint) */
    [data-testid="stMetricDelta"] span {
        color: #059669;
    }

    /* ---------- Tables ---------- */
    .note-card [data-testid="stDataFrame"] {
        font-size: 0.8rem;
    }

    .note-card table {
        border-radius: 10px;
        overflow: hidden;
    }

    .note-card thead {
        background: #f9fafb;
    }

    .note-card tbody tr:nth-child(even) {
        background: #f9fafb;
    }

    /* ---------- Charts ---------- */
    /* give charts a clean white card-style background */
    .chart-card [data-testid="stPlotlyChart"],
    .chart-card [data-testid="stAltairChart"],
    .chart-card canvas {
        background: #ffffff !important;
    }

    /* ---------- Links & bullets ---------- */
    a {
        color: #1f2937;
        text-decoration: none;
        border-bottom: 1px dotted rgba(31,41,55,0.45);
    }

    a:hover {
        color: #111827;
        border-bottom-style: solid;
    }

    /* headline bullets tighter */
    .card ul li a {
        font-size: 0.9rem;
    }

    /* ---------- Strategist Playbook ---------- */
    .card strong {
        font-weight: 600;
        color: #111827;
    }

    /* subtle blush tint only for PLAYBOOK background if you want it differentiated
       (comment the next rule out if you prefer pure white) */
    .card.playbook {
        background: #fff7f7;
    }

    /* ---------- Misc ---------- */
    footer, .reportview-container .main footer {
        visibility: hidden;
        height: 0;
    }
    </style>
    """

    st.markdown(css, unsafe_allow_html=True)
