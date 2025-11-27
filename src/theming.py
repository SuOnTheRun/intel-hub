# src/theming.py
from __future__ import annotations
import streamlit as st

def _apply_white_lux_theme() -> None:
    """
    Core 'white luxury control hub' theme for both pages.
    """
    st.set_page_config(
        page_title="Blis Intelligence Hub",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    css = """
    <style>

    /* ---------- Base app ---------- */
    .stApp {
        background: #f5f5f7;
        color: #111827;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }

    .main .block-container {
        max-width: 1400px;
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: #f3f4f6;
        border-right: 1px solid #e5e7eb;
    }

    section[data-testid="stSidebar"] .css-1d391kg,
    section[data-testid="stSidebar"] .block-container {
        padding-top: 1.5rem !important;
    }

    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 0.9rem !important;
        text-transform: uppercase;
        letter-spacing: .12em;
        color: #6b7280 !important;
        font-weight: 600 !important;
    }

    /* ---------- Typography ---------- */
    h1 {
        font-size: 1.9rem !important;
        letter-spacing: .02em;
        font-weight: 650 !important;
        margin-bottom: 0.4rem !important;
        color: #111827;
    }

    h3.section-title {
        background: transparent !important;
        padding: 0 !important;
        margin-top: 0.5rem !important;
        font-size: 0.95rem !important;
        text-transform: uppercase;
        letter-spacing: .11em;
        color: #4b5563 !important;
        font-weight: 600 !important;
    }

    .calc-note {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 0.15rem;
    }

    .small {
        font-size: 0.78rem;
        color: #6b7280;
    }

    /* ---------- Cards ---------- */
    .card, .chart-card, .note-card {
        background: #ffffff !important;
        border-radius: 16px !important;
        border: 1px solid #e5e7eb !important;
        padding: 1rem 1.25rem !important;
        margin-top: 0.75rem !important;
        box-shadow:
            0 18px 45px rgba(15, 23, 42, 0.04),
            0 0 1px rgba(15, 23, 42, 0.08);
    }

    .chart-card {
        padding: 0.9rem !important;
    }

    /* ---------- Metric boxes ---------- */
    [data-testid="stMetric"] {
        background: #ffffff !important;
        border-radius: 14px !important;
        border: 1px solid #e5e7eb !important;
        padding: 0.65rem 0.75rem !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
    }

    [data-testid="stMetric"] label {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        color: #6b7280 !important;
        letter-spacing: .14em;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.3rem !important;
        font-weight: 650 !important;
        color: #111827 !important;
    }

    /* ---------- Tables ---------- */
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

    /* ---------- Links ---------- */
    a {
        color: #1f2937;
        border-bottom: 1px dotted rgba(31,41,55,0.45);
        text-decoration: none;
    }

    a:hover {
        border-bottom-style: solid;
        color: #111827;
    }

    footer { visibility: hidden; height: 0; }

    </style>
    """

    st.markdown(css, unsafe_allow_html=True)


def set_dark_theme() -> None:
    """Used by the US Command Center page."""
    _apply_white_lux_theme()


def set_light_theme() -> None:
    """Used by the Markets & Macro page — same theme for now."""
    _apply_white_lux_theme()
