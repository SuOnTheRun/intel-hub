# src/theming.py
from __future__ import annotations
import streamlit as st

def apply_white_lux_theme() -> None:
    """
    Inject white-luxury design theme (no page_config here).
    """
    css = """
    <style>

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

    section[data-testid="stSidebar"] {
        background: #f3f4f6;
        border-right: 1px solid #e5e7eb;
    }

    h1 {
        font-size: 1.9rem !important;
        font-weight: 650 !important;
        margin-bottom: 0.4rem !important;
        color: #111827;
    }

    .card, .chart-card {
        background: #ffffff !important;
        border-radius: 16px !important;
        border: 1px solid #e5e7eb !important;
        padding: 1rem 1.25rem !important;
        margin-top: 0.75rem !important;
        box-shadow:
            0 18px 45px rgba(15, 23, 42, 0.04),
            0 0 1px rgba(15, 23, 42, 0.08);
    }

    [data-testid="stMetric"] {
        background: #ffffff !important;
        border-radius: 14px !important;
        border: 1px solid #e5e7eb !important;
        padding: 0.65rem 0.75rem !important;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
    }

    footer { visibility: hidden; height: 0; }

    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

