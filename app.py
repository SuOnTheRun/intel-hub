# src/app.py — Intelligence Hub (US) minimal stable app
from __future__ import annotations

import os
import pandas as pd
import streamlit as st

# --- Safe theming hook (works even if src/theming.py doesn't exist) ---
def inject_css() -> None:
    """No-op unless theming module is present."""
    pass

try:
    # If you have src/theming.py with inject_css(), we'll use it.
    from src.theming import inject_css as _inject_css  # type: ignore
    inject_css = _inject_css  # override no-op
except Exception:
    pass

# --- Collectors ---
from src.collectors import (
    NewsCollector,
    GovCollector,
    MacroCollector,
    TrendsCollector,
    MobilityCollector,
    StocksCollector,
)

st.set_page_config(
    page_title="Intelligence Hub — US",
    page_icon=None,
    layout="wide",
)

# Optional custom CSS (quiet luxury look if you provided it in theming.py)
inject_css()

# -----------------------
# Sidebar controls
# -----------------------
st.sidebar.title("Intelligence Hub — US")

CATEGORIES = [
    "Macro",
    "Technology",
    "Consumer",
    "Energy",
    "Healthcare",
    "Finance",
    "Retail",
    "Autos",
]

selected_cats = st.sidebar.multiselect("Categories", CATEGORIES, default=["Macro", "Technology", "Consumer"])

lookback_days = int(st.sidebar.slider("Lookback (days)", min_value=1, max_value=14, value=3))
max_per_source = int(st.sidebar.slider("Max stories per source", min_value=20, max_value=200, value=80))

source_block = st.sidebar.expander("Sources", expanded=False)
with source_block:
    st.caption("All data from public/free sources. Updated on load.")

# -----------------------
# Data pulls
# -----------------------
news_df = NewsCollector().collect(selected_cats, max_items=max_per_source, lookback_days=lookback_days)
gov_df  = GovCollector().collect(max_items=120, lookback_days=lookback_days)
macro_trends_df = MacroCollector().collect(lookback_days=lookback_days)   # Google Trends macro pulse
trends_df = TrendsCollector().collect(selected_cats, lookback_days=max(7, lookback_days))
mobility_df = MobilityCollector().collect()

# Example stock tickers — you can change these in code later
ticker_list = ["^NDX", "AAPL", "NVDA", "AMZN", "TSLA", "MSFT"]
try:
    stocks_df = StocksCollector().collect(tickers=ticker_list)
except Exception:
    stocks_df = pd.DataFrame(columns=["ticker", "price", "change", "pct", "volume"])


# -----------------------
# Layout
# -----------------------
st.markdown("## Command Center")

kpi_cols = st.columns(5)
with kpi_cols[0]:
    st.metric("News items (filtered)", int(len(news_df)))
with kpi_cols[1]:
    st.metric("Gov/Reg updates", int(len(gov_df)))
with kpi_cols[2]:
    st.metric("Macro points (pytrends)", int(len(macro_trends_df)))
with kpi_cols[3]:
    st.metric("Mobility rows (TSA)", int(len(mobility_df)))
with kpi_cols[4]:
    st.metric("Tracked tickers", int(len(stocks_df)))

st.divider()

# -----------------------
# News & Gov
# -----------------------
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Latest Headlines")
    if news_df.empty:
        st.info("No headlines returned for the current lookback. Try increasing the lookback window.")
    else:
        # Show a concise table
        show_cols = ["published_dt", "category", "source", "title", "link"]
        st.dataframe(news_df[show_cols].head(200), use_container_width=True)

with col2:
    st.subheader("Gov / Regulatory")
    if gov_df.empty:
        st.info("No recent regulator/government items for the selected window.")
    else:
        show_cols = ["published_dt", "source", "title", "link"]
        st.dataframe(gov_df[show_cols].head(120), use_container_width=True)

st.divider()

# -----------------------
# Macro & Trends
# -----------------------
tcol1, tcol2 = st.columns(2)
with tcol1:
    st.subheader("Macro pulse (Google Trends)")
    if macro_trends_df.empty:
        st.info("Macro pulse unavailable right now.")
    else:
        st.line_chart(
            macro_trends_df.set_index("timestamp").drop(columns=[c for c in macro_trends_df.columns if c not in ["timestamp"]])
        )

with tcol2:
    st.subheader("Category trends (Google Trends)")
    if trends_df.empty:
        st.info("No category trends for selection.")
    else:
        # Multiple terms; aggregate by timestamp for a simple pulse
        plot_df = trends_df.rename(columns={"timestamp": "ts"}).copy()
        try:
            # pivot to show one line per selected category-group
            plot_df["value"] = 1  # dummy so we can show count-of-interest points
            plot_df = (
                plot_df.groupby(["ts", "category"])["value"]
                .sum()
                .reset_index()
                .pivot(index="ts", columns="category", values="value")
                .fillna(0.0)
            )
            st.line_chart(plot_df)
        except Exception:
            st.dataframe(trends_df.head(200), use_container_width=True)

st.divider()

# -----------------------
# Mobility & Stocks
# -----------------------
bcol1, bcol2 = st.columns(2)
with bcol1:
    st.subheader("Mobility — TSA throughput (last 30)")
    if mobility_df.empty:
        st.info("TSA dataset unavailable right now.")
    else:
        mplot = mobility_df.sort_values("date").set_index("date")["throughput"]
        st.line_chart(mplot)

with bcol2:
    st.subheader("Market snapshot")
    if stocks_df.empty:
        st.info("Stock quotes unavailable.")
    else:
        st.dataframe(stocks_df, use_container_width=True)

st.caption("External, free sources only. Timestamps are UTC.")
