# MUST COME FIRST
import streamlit as st
st.set_page_config(
    page_title="Markets & Macro Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

from theming import apply_white_lux_theme
apply_white_lux_theme()

# src/ui_markets.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np

from .theming import set_light_theme
from .collectors import fetch_market_snapshot
from .risk_model import market_momentum

def render():
    set_light_theme()
    st.title("United States — Markets & Macro")

    snap, hist = ({}, pd.DataFrame())
    try:
        snap, hist = fetch_market_snapshot()
    except Exception:
        pass

    c1, c2, c3 = st.columns([1.1,1.1,1.1])
    with c1:
        st.metric("S&P 500 (close)", f"{snap.get('S&P 500', '—')}")
    with c2:
        st.metric("Nasdaq 100 (close)", f"{snap.get('Nasdaq 100', '—')}")
    with c3:
        st.metric("VIX (close)", f"{snap.get('VIX', '—')}")

    if not hist.empty:
        st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
        st.subheader("Equity Indices")
        st.line_chart(hist[["S&P 500","Nasdaq 100"]].dropna(), use_container_width=True, height=260)
        mom = market_momentum(hist)
        st.caption(f"20-day momentum — S&P 500: {mom.get('S&P 500',0):+.2f}% · Nasdaq 100: {mom.get('Nasdaq 100',0):+.2f}%")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Market history unavailable right now.")

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("Sources: yfinance (indices).")
