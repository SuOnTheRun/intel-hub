# src/ui_markets.py
import streamlit as st
import pandas as pd
from .theming import set_dark_theme
from .collectors import fetch_market_snapshot

def render():
    set_dark_theme()
    st.title("Markets & Macro — Strategy Lens")
    st.caption("Translate market & economic conditions into advertising strategy.")

    snap, idx = fetch_market_snapshot()  # uses yfinance, free

    left, right = st.columns([1.6, 1.2])

    with left:
        if isinstance(idx, pd.DataFrame) and not idx.empty:
            st.subheader("Index performance")
            plot_df = idx[["S&P 500","Nasdaq 100"]].dropna()
            st.line_chart(plot_df, use_container_width=True, height=220)
            # Simple regime hint: 50/200 cross
            spx = plot_df["S&P 500"].dropna()
            ma50 = spx.rolling(50).mean()
            ma200 = spx.rolling(200).mean()
            if len(ma200.dropna()):
                regime = "Uptrend (50>200)" if ma50.iloc[-1] > ma200.iloc[-1] else "Downtrend (50<200)"
                implication = ("Favour performance/scale tests; broaden reach in growth contexts."
                               if regime.startswith("Uptrend") else
                               "Tighten efficiency targets; emphasise value framing and brand safety.")
                st.markdown(f"**Regime:** {regime} · **Implication:** {implication}")

    with right:
        if isinstance(snap, dict) and snap:
            st.subheader("Snapshot")
            rows = [f"- **{k}**: {v:.2f}" for k, v in snap.items()]
            st.markdown("\n".join(rows))

    st.markdown("---")
    st.caption("Sources: yfinance (^GSPC, ^NDX, ^VIX). Regime via S&P 500 50/200 DMA cross (informative, not advice).")
