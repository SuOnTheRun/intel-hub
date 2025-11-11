"""Intelligence Hub — Streamlit app"""

from __future__ import annotations

import os
import json
import time
# ... the rest of your imports and code ...
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import time

st.set_page_config(page_title="Intelligence Hub — US", layout="wide")

def safe(fn, fallback):
    @wraps(fn)
    def _inner(*a, **k):
        try:
            return fn(*a, **k)
        except Exception:
            return fallback
    return _inner

# 10-min cache across restarts to beat cold starts
@st.cache_data(ttl=600)
def cached_news(categories, max_items, lookback_days):
    from src.collectors import NewsCollector
    return NewsCollector().collect(categories, max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_gov(max_items, lookback_days):
    # Match the class name you actually have (GovCollector or GovRegCollector)
    from src.collectors import GovCollector as _Gov
    return _Gov().collect(max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_macro():
    from src.collectors import MacroTrendsCollector as _M
    return _M().collect()

@st.cache_data(ttl=600)
def cached_category_trends(categories):
    from src.collectors import CategoryTrendsCollector as _C
    return _C().collect(categories)

@st.cache_data(ttl=600)
def cached_mobility():
    from src.collectors import MobilityCollector as _Mob
    return _Mob().collect()

@st.cache_data(ttl=600)
def cached_stocks(tickers):
    from src.collectors import StocksCollector as _S
    return _S().collect(tickers)


# src/app.py — Intelligence Hub (US) minimal stable app
from __future__ import annotations

left, right = st.columns([1,4])

# --- Sidebar controls (unchanged) ---
with left:
    st.markdown("### Intelligence Hub — US")
    cats = st.multiselect("Categories", ["Macro","Technology","Consumer"], default=["Macro","Technology","Consumer"])
    lookback = st.slider("Lookback (days)", 1, 14, 3)
    max_per_source = st.slider("Max stories per source", 20, 200, 80)
    st.selectbox("Sources", [" "], index=0)

with right:
    st.header("Command Center")
    placeholder = st.empty()
    st.caption("External, free sources only. Timestamps are UTC.")

    # 1) Always render fast with NEWS first
    news_df = cached_news(cats, max_items=max_per_source, lookback_days=lookback)
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("News items (filtered)", len(news_df) if not news_df.empty else 0)

    # paint the table immediately
    st.subheader("Latest Headlines")
    if news_df.empty:
        st.info("No headlines returned for the current lookback. Try increasing the lookback window.")
    else:
        st.dataframe(news_df[["published_dt","category","source","title"]].head(25), use_container_width=True, hide_index=True)

    # 2) Kick off the heavier collectors in parallel with strict timeouts
    tasks = {
        "gov": lambda: cached_gov(50, lookback),
        "macro": lambda: cached_macro(),
        "cat": lambda: cached_category_trends(cats),
        "tsa": lambda: cached_mobility(),
        "stocks": lambda: cached_stocks(["^NDX","NVDA","AAPL","MSFT"])
    }

    results = {k: None for k in tasks}
    with ThreadPoolExecutor(max_workers=5) as ex:
        fut_map = {ex.submit(tasks[k]): k for k in tasks}
        start = time.time()
        for fut in as_completed(fut_map, timeout=20):  # hard wall so proxy never 502s
            k = fut_map[fut]
            try:
                results[k] = fut.result()
            except Exception:
                results[k] = None
            if time.time() - start > 20:
                break

    # 3) Render each panel defensively
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Gov / Regulatory")
        gov = results["gov"]
        if gov is None or getattr(gov, "empty", True):
            st.info("No recent regulator/government items for the selected window.")
        else:
            st.dataframe(gov[["published_dt","source","title"]].head(15), use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Macro pulse (Google Trends)")
        macro = results["macro"]
        if macro is None or getattr(macro, "empty", True):
            st.info("Macro pulse unavailable right now.")
        else:
            st.line_chart(macro.set_index(macro.columns[0]).drop(columns=[c for c in macro.columns if c.lower() in ("ispartial","category")]), height=220)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Category trends (Google Trends)")
        catdf = results["cat"]
        if catdf is None or getattr(catdf, "empty", True):
            st.info("No category trends for selection.")
        else:
            piv = catdf.pivot_table(index="date", columns="category", values="value", aggfunc="mean")
            st.line_chart(piv, height=220)

    with col4:
        st.subheader("Mobility — TSA throughput (last 30)")
        tsa = results["tsa"]
        if tsa is None or getattr(tsa, "empty", True):
            st.info("TSA dataset unavailable right now.")
        else:
            st.line_chart(tsa.set_index("date")["throughput"], height=220)

    st.subheader("Market snapshot")
    stocks = results["stocks"]
    if stocks is None or getattr(stocks, "empty", True):
        st.info("Stock quotes unavailable.")
    else:
        st.dataframe(stocks, use_container_width=True, hide_index=True)

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
