# app.py — Intelligence Hub — US (safe boot, lazy load, exec-ready)

import os
import pandas as pd
import streamlit as st

from src.theming import inject_css if 'theming' in __import__('pkgutil').iter_modules(['src']) else (lambda: None)

# Required collectors (already hardened in src/collectors.py)
from src.collectors import (
    NewsCollector, GovCollector, SocialCollector,
    MacroCollector, TrendsCollector, MobilityCollector, StocksCollector
)
# Optional analytics (must fail-soft if missing)
try:
    from src.analytics import aggregate_category_metrics, compute_risk_index
except Exception:
    def aggregate_category_metrics(*_a, **_k): return pd.DataFrame()
    def compute_risk_index(*_a, **_k): return pd.DataFrame(columns=["category","tension_index"])

st.set_page_config(page_title="Intelligence Hub — US", layout="wide")
inject_css()

# --------------- Sidebar ---------------
st.sidebar.header("Intelligence Hub — US")
cats_all = ["Macro", "Technology", "Consumer", "Energy", "Healthcare", "Finance", "Retail", "Autos"]
selected_cats = st.sidebar.multiselect("Categories", cats_all, default=["Macro", "Technology", "Consumer"])
lookback_days = st.sidebar.slider("Lookback (days)", 1, 14, 3)
max_items = st.sidebar.slider("Max stories per source", 20, 200, 80)
st.sidebar.caption("All data from public/free sources. Updated on demand.")

SAFE_BOOT = os.environ.get("SAFE_BOOT", "0") == "1"

# --------------- Controls ---------------
colA, colB, colC = st.columns([1,1,4])
with colA:
    go = st.button("Load / Refresh", type="primary", use_container_width=True)
with colB:
    clear = st.button("Clear Cache", use_container_width=True)

if clear:
    st.cache_data.clear()
    st.success("Cache cleared.")

# --------------- Diagnostics bucket ---------------
errors: list[str] = []
def safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:
        errors.append(f"{fn.__name__}: {e}")
        return pd.DataFrame()

# --------------- Cached wrappers ---------------
@st.cache_data(ttl=600, show_spinner=False)
def _news(cats, max_items, lookback_days):
    return NewsCollector().collect(cats, max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600, show_spinner=False)
def _gov(max_items, lookback_days):
    return GovCollector().collect(max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600, show_spinner=False)
def _social(cats, max_items, lookback_days):
    return SocialCollector().collect(cats, max_items=max_items, lookback_days=lookback_days)

@st.cache_data(ttl=600, show_spinner=False)
def _macro(lookback_days):
    return MacroCollector().collect(lookback_days=lookback_days)

@st.cache_data(ttl=600, show_spinner=False)
def _trends(cats):
    return TrendsCollector().collect(cats, lookback_days=30)

@st.cache_data(ttl=600, show_spinner=False)
def _mobility():
    return MobilityCollector().collect()

@st.cache_data(ttl=600, show_spinner=False)
def _stocks():
    # Lightweight daily pulse – safe on free tier
    tickers = ["^GSPC","^IXIC","^DJI","AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA"]
    return StocksCollector().collect(tickers)

# --------------- First paint: always immediate ---------------
st.info("Service healthy. Click **Load / Refresh** to pull live signals.", icon=None)

if SAFE_BOOT and not go:
    st.warning("SAFE_BOOT is enabled — collectors are idle. Set SAFE_BOOT=0 to enable data.")
    st.stop()

if not go and not SAFE_BOOT:
    st.stop()

# --------------- Live pull (guarded) ---------------
with st.spinner("Collecting live signals…"):
    news    = safe(_news, selected_cats, max_items, lookback_days)
    gov     = safe(_gov, 120, lookback_days)
    social  = safe(_social, selected_cats, 120, lookback_days)
    macro   = safe(_macro, lookback_days)
    trends  = safe(_trends, selected_cats)
    mobility= safe(_mobility)
    stocks  = safe(_stocks)

# --------------- KPI & Risk (guarded) ---------------
try:
    kpis = aggregate_category_metrics(news, social, trends, stocks)
except Exception as e:
    errors.append(f"aggregate_category_metrics: {e}")
    kpis = pd.DataFrame()

try:
    risk = compute_risk_index(news, social, trends, stocks)
except Exception as e:
    errors.append(f"compute_risk_index: {e}")
    risk = pd.DataFrame(columns=["category","tension_index"])

# --------------- Layout ---------------
t1, t2 = st.tabs(["Command Center", "Feeds"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.subheader("Market & Macro Pulse")
        if not stocks.empty:
            st.dataframe(stocks, use_container_width=True, height=280)
        if not macro.empty:
            st.line_chart(macro.set_index("timestamp").iloc[:, :5], height=240)

    with c2:
        st.subheader("Risk Index")
        if not risk.empty:
            st.dataframe(risk, use_container_width=True, height=240)
        st.subheader("Mobility")
        if not mobility.empty:
            st.bar_chart(mobility.set_index("date")["throughput"].sort_index(), height=240)

with t2:
    st.subheader("Government / Regulatory")
    if not gov.empty:
        st.dataframe(gov[["published_dt","source","title"]].head(200), use_container_width=True, height=320)
    st.subheader("News")
    if not news.empty:
        st.dataframe(news[["published_dt","category","source","title"]].head(300), use_container_width=True, height=420)
    st.subheader("Social / Community")
    if not social.empty:
        st.dataframe(social[["published_dt","category","source","title"]].head(300), use_container_width=True, height=420)

# Diagnostics (if anything failed)
if errors:
    st.markdown("#### Diagnostics")
    for e in errors:
        st.code(e)
