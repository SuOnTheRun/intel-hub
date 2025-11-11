# src/app.py — Intelligence Hub (US)

"""Streamlit UI for the Intelligence Hub — US"""

import os
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

# ---------- Streamlit page config (must be early) ----------
st.set_page_config(
    page_title="Intelligence Hub — US",
    page_icon=None,
    layout="wide",
)

# Fail-fast guard: never let import-time errors kill the process
try:
    import pandas as pd  # light
except Exception:
    import streamlit as st
    st.write("Boot error: pandas not available")
    raise


# ---------- Optional theming hook (safe if theming.py absent) ----------
def inject_css() -> None:
    """No-op unless src/theming.py is present with inject_css()."""
    pass

try:
    from src.theming import inject_css as _inject_css  # type: ignore
    inject_css = _inject_css
except Exception:
    pass

inject_css()

# ---------- Collectors ----------
from src.collectors import (
    NewsCollector,
    GovCollector,
    MacroCollector,
    TrendsCollector,
    MobilityCollector,
    StocksCollector,
)

# ---------- Helpers ----------
def safe_call(f, *a, **k):
    """Run a function, return None on any error (and keep UI alive)."""
    try:
        return f(*a, **k)
    except Exception:
        return None

# 10-min cache across restarts to beat cold starts
@st.cache_data(ttl=600)
def cached_news(categories: List[str], max_items: int, lookback_days: int) -> pd.DataFrame:
    return NewsCollector().collect(categories, max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_gov(max_items: int, lookback_days: int) -> pd.DataFrame:
    return GovCollector().collect(max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_macro(lookback_days: int) -> pd.DataFrame:
    return MacroCollector().collect(lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_trends(categories: List[str], lookback_days: int) -> pd.DataFrame:
    return TrendsCollector().collect(categories, lookback_days=lookback_days)

@st.cache_data(ttl=600)
def cached_mobility() -> pd.DataFrame:
    return MobilityCollector().collect()

@st.cache_data(ttl=600)
def cached_stocks(tickers: List[str]) -> pd.DataFrame:
    return StocksCollector().collect(tickers=tickers)

# ---------- Sidebar ----------
st.sidebar.title("Intelligence Hub — US")

CATEGORIES = [
    "Macro", "Technology", "Consumer",
    "Energy", "Healthcare", "Finance",
    "Retail", "Autos",
]
selected_cats = st.sidebar.multiselect(
    "Categories", CATEGORIES, default=["Macro", "Technology", "Consumer"]
)

lookback_days = int(st.sidebar.slider("Lookback (days)", 1, 14, 3))
max_per_source = int(st.sidebar.slider("Max stories per source", 20, 200, 80))

with st.sidebar.expander("Sources", expanded=False):
    st.caption("All data from public/free sources. Updated on load. Timestamps are UTC.")

# ---------- Data pulls ----------
# Always fetch NEWS first so the page paints quickly
news_df = safe_call(cached_news, selected_cats, max_per_source, lookback_days)
if news_df is None:
    news_df = pd.DataFrame(columns=["published_dt", "category", "source", "title", "link"])

# Kick off the rest in parallel with tight timeouts to avoid 502s on Render free tier
tasks = {
    "gov":      lambda: cached_gov(120, lookback_days),
    "macro":    lambda: cached_macro(lookback_days),
    "trends":   lambda: cached_trends(selected_cats, max(7, lookback_days)),
    "mobility": lambda: cached_mobility(),
    "stocks":   lambda: cached_stocks(["^NDX", "AAPL", "NVDA", "AMZN", "TSLA", "MSFT"]),
}
results: Dict[str, Any] = {k: None for k in tasks}

start = time.time()
with ThreadPoolExecutor(max_workers=4) as ex:
    fut_map = {ex.submit(tasks[k]): k for k in tasks}
    for fut in as_completed(fut_map, timeout=22):
        k = fut_map[fut]
        try:
            results[k] = fut.result(timeout=1)
        except Exception:
            results[k] = None
        if time.time() - start > 22:
            break

gov_df      = results["gov"]      if isinstance(results["gov"], pd.DataFrame) else pd.DataFrame()
macro_df    = results["macro"]    if isinstance(results["macro"], pd.DataFrame) else pd.DataFrame()
trends_df   = results["trends"]   if isinstance(results["trends"], pd.DataFrame) else pd.DataFrame()
mobility_df = results["mobility"] if isinstance(results["mobility"], pd.DataFrame) else pd.DataFrame()
stocks_df   = results["stocks"]   if isinstance(results["stocks"], pd.DataFrame) else pd.DataFrame(
    columns=["ticker", "price", "change", "pct", "volume"]
)

# ---------- Layout ----------
st.markdown("## Command Center")

kpi_cols = st.columns(5)
kpi_cols[0].metric("News items (filtered)", int(len(news_df)))
kpi_cols[1].metric("Gov/Reg updates", int(len(gov_df)))
kpi_cols[2].metric("Macro points (pytrends)", int(len(macro_df)))
kpi_cols[3].metric("Mobility rows (TSA)", int(len(mobility_df)))
kpi_cols[4].metric("Tracked tickers", int(len(stocks_df)))

st.divider()
# Right after st.markdown("## Command Center")
st.markdown("## Command Center")
if st.button("↻ Retry data pulls", type="secondary"):
    st.cache_data.clear()  # clear cached None results
    st.experimental_rerun()

# ---------- Layout ----------
st.markdown("## Command Center")

# ✅ Add this block right below the line above:
# ----------------------------------------------------
if "boot_stage" not in st.session_state:
    st.session_state.boot_stage = 0

# Add a quick Retry button
if st.button("↻ Retry data pulls", type="secondary"):
    st.cache_data.clear()            # clear old cached results
    st.session_state.boot_stage = 1  # allow full data fetch next run
    st.experimental_rerun()

# On the very first render, paint only the fast section (NEWS)
run_heavy = st.session_state.boot_stage >= 1
# Automatically advance to full mode after first paint
if st.session_state.boot_stage == 0:
    st.session_state.boot_stage = 1
    st.experimental_rerun()
# ----------------------------------------------------

kpi_cols = st.columns(5)
kpi_cols[0].metric("News items (filtered)", int(len(news_df)))

# ----- News & Gov -----
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Latest Headlines")
    if news_df.empty:
        st.info("No headlines returned for the current lookback. Try increasing the lookback window.")
    else:
        show_cols = [c for c in ["published_dt", "category", "source", "title", "link"] if c in news_df.columns]
        st.dataframe(news_df[show_cols].head(200), use_container_width=True, hide_index=True)

with col2:
    st.subheader("Gov / Regulatory")
    if gov_df.empty:
        st.info("No recent regulator/government items for the selected window.")
    else:
        show_cols = [c for c in ["published_dt", "source", "title", "link"] if c in gov_df.columns]
        st.dataframe(gov_df[show_cols].head(120), use_container_width=True, hide_index=True)

st.divider()

# ----- Macro & Category Trends -----
tcol1, tcol2 = st.columns(2)

with tcol1:
    st.subheader("Macro pulse (Google Trends)")
    if macro_df.empty:
        st.info("Macro pulse unavailable right now.")
    else:
        # Expect a time column named 'timestamp'
        try:
            plot_df = macro_df.copy()
            if "timestamp" in plot_df.columns:
                plot_df = plot_df.set_index("timestamp")
            # Drop non-series columns if present
            drop_cols = [c for c in plot_df.columns if c.lower() in ("ispartial", "category")]
            plot_df = plot_df.drop(columns=drop_cols, errors="ignore")
            st.line_chart(plot_df, height=220)
        except Exception:
            st.dataframe(macro_df.head(200), use_container_width=True)

with tcol2:
    st.subheader("Category trends (Google Trends)")
    if trends_df.empty:
        st.info("No category trends for selection.")
    else:
        try:
            plot_df = trends_df.copy()
            # Accept either 'timestamp' or 'date' as the x-axis
            xcol = "timestamp" if "timestamp" in plot_df.columns else ("date" if "date" in plot_df.columns else None)
            if xcol is not None:
                plot_df[xcol] = pd.to_datetime(plot_df[xcol], errors="coerce", utc=True)
                plot_df = plot_df.dropna(subset=[xcol])
                # If there are 'term'/'interest' columns, pivot them; else try category/value
                if {"term", "interest"}.issubset(plot_df.columns):
                    piv = plot_df.pivot_table(index=xcol, columns="term", values="interest", aggfunc="mean")
                elif {"category", "value"}.issubset(plot_df.columns):
                    piv = plot_df.pivot_table(index=xcol, columns="category", values="value", aggfunc="mean")
                else:
                    piv = plot_df.set_index(xcol)
                st.line_chart(piv, height=220)
            else:
                st.dataframe(trends_df.head(200), use_container_width=True)
        except Exception:
            st.dataframe(trends_df.head(200), use_container_width=True)

st.divider()

# ----- Mobility & Stocks -----
bcol1, bcol2 = st.columns(2)

with bcol1:
    st.subheader("Mobility — TSA throughput (last 30)")
    if mobility_df.empty:
        st.info("TSA dataset unavailable right now.")
    else:
        try:
            mplot = mobility_df.sort_values("date").set_index("date")["throughput"]
            st.line_chart(mplot, height=220)
        except Exception:
            st.dataframe(mobility_df.head(60), use_container_width=True)

with bcol2:
    st.subheader("Market snapshot")
    if stocks_df.empty:
        st.info("Stock quotes unavailable.")
    else:
        st.dataframe(stocks_df, use_container_width=True, hide_index=True)

st.caption("External, free sources only. Timestamps are UTC.")
