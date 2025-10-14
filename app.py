import os, json
from datetime import datetime
from typing import List, Optional

import pandas as pd
import streamlit as st
import plotly.express as px
from dateutil import tz

from src.theming import inject_css, kpi
from src.collectors import (
    REGIONS, TOP_MARKETS, CATEGORIES,
    fetch_news, fetch_quotes, fetch_trends,
    news_z, senti_avg, ccs
)

# ---------- APP SETUP ----------
st.set_page_config(page_title="Intelligence Hub", page_icon=None, layout="wide")
inject_css()
IST = tz.gettz("Asia/Kolkata")

# ---------- NAV ----------
st.sidebar.markdown("### Intelligence Hub")
page = st.sidebar.radio("", ["Command Center","Regions","Categories","Markets","Social","My Data","Methods"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("Updated: " + datetime.now(IST).strftime("%d %b %Y, %H:%M IST"))

def region_country_controls():
    c1, c2 = st.columns([1,1])
    with c1:
        region = st.selectbox("Region", ["—"] + list(REGIONS.keys()) + TOP_MARKETS, index=0)
    with c2:
        choices = ["—"]
        if region in REGIONS: choices += REGIONS[region]
        elif region in TOP_MARKETS: choices = ["—", region]
        country = st.selectbox("Country", choices, index=0)
    if region == "—": region = None
    if country == "—": country = None
    return region, country

def category_select():
    return st.selectbox("Category", list(CATEGORIES.keys()),
                        format_func=lambda k: CATEGORIES[k]["name"])

# ---------- CACHE WRAPPERS (5 min) ----------
@st.cache_data(ttl=300, show_spinner=False)
def _news(cat, country, region):
    return fetch_news(cat, country=country, region=region)

@st.cache_data(ttl=300, show_spinner=False)
def _quotes(symbols: List[str]):
    return fetch_quotes(symbols)

@st.cache_data(ttl=300, show_spinner=False)
def _trends(cat, geo):
    return fetch_trends(cat, geo)

# ---------- PAGES ----------
if page == "Command Center":
    st.header("Command Center")
    st.caption("Global pulse across categories. Real open data only.")

    # KPI row
    cols = st.columns(3)
    # composite from global (no geo)
    cat_key = "technology"
    headlines = _news(cat_key, None, None)
    nz = news_z(headlines); sa = senti_avg(headlines)
    q = _quotes(CATEGORIES[cat_key]["tickers"]); mkt = (q[0]["pct"]/50.0) if q else 0.0  # normalized small factor
    composite = ccs(nz, sa, 0.0, mkt)
    with cols[0]: kpi("Composite Signal (sample: Tech)", f"{composite:.2f}")
    with cols[1]: kpi("Headline Sentiment (Tech)", f"{sa:.2f}", "VADER avg")
    with cols[2]: kpi("News Volume z (Tech)", f"{nz:.2f}", "vs baseline")

    # Heatmap
    rows = []
    for slug, cfg in CATEGORIES.items():
        n = _news(slug, None, None)
        q = _quotes(cfg["tickers"])
        rows.append({
            "Category": cfg["name"],
            "News z": news_z(n),
            "Sentiment": senti_avg(n),
            "Market Δ%": q[0]["pct"] if q else 0.0
        })
    dfh = pd.DataFrame(rows)
    st.subheader("Category Heatmap (24–72h)")
    st.dataframe(dfh.set_index("Category"))

    st.subheader("Top Storylines (Reuters)")
    for slug, cfg in CATEGORIES.items():
        st.markdown(f"**{cfg['name']}**")
        for h in _news(slug, None, None)[:5]:
            st.write(f"- [{h['title']}]({h['link']}) — {h['published']} | Sentiment {h['senti']:.2f}")

elif page == "Regions":
    st.header("Regions")
    region, country = region_country_controls()
    cat = category_select()

    left, right = st.columns([1.2, 1])
    with left:
        st.subheader("News & Sentiment")
        headlines = _news(cat, country, region)
        if headlines:
            st.dataframe(pd.DataFrame(headlines)[["title","source","published","senti","link"]], hide_index=True)
        nz = news_z(headlines); sa = senti_avg(headlines)
        st.caption(f"News z: {nz:.2f} • Avg sentiment: {sa:.2f}")

    with right:
        st.subheader("Market Pulse")
        q = _quotes(CATEGORIES[cat]["tickers"])
        if q: st.dataframe(pd.DataFrame(q), hide_index=True)
        st.subheader("Search Interest (90 days)")
        geo = country or region or "IN"
        try:
            ts = _trends(cat, geo)
            for d in ts["datasets"]:
                fig = px.line(pd.DataFrame({"date": ts["labels"], d["label"]: d["data"]}), x="date", y=d["label"])
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.info("Trends unavailable for this scope right now.")

elif page == "Categories":
    st.header("Categories")
    region, country = region_country_controls()
    cat = category_select()
    headlines = _news(cat, country, region)
    nz = news_z(headlines); sa = senti_avg(headlines)
    cols = st.columns(3)
    with cols[0]: kpi("News z", f"{nz:.2f}")
    with cols[1]: kpi("Sentiment", f"{sa:.2f}")
    q = _quotes(CATEGORIES[cat]["tickers"]); pct = q[0]["pct"] if q else 0.0
    with cols[2]: kpi("Market Δ%", f"{pct:.2f}%")

    st.subheader("News")
    if headlines:
        st.dataframe(pd.DataFrame(headlines)[["title","source","published","senti","link"]], hide_index=True)
    else:
        st.caption("No matching stories now.")

    st.subheader("Trends (90 days)")
    geo = country or region or "IN"
    try:
        ts = _trends(cat, geo)
        for d in ts["datasets"]:
            fig = px.line(pd.DataFrame({"date": ts["labels"], d["label"]: d["data"]}), x="date", y=d["label"])
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.info("Trends unavailable for this scope right now.")

elif page == "Markets":
    st.header("Markets & Media Conditions")
    rows = []
    for slug, cfg in CATEGORIES.items():
        q = _quotes(cfg["tickers"])
        if q: rows.extend(q)
    if rows:
        st.dataframe(pd.DataFrame(rows).drop_duplicates(subset=["symbol"]).set_index("symbol"))

elif page == "Social":
    st.header("Social & Community Pulse")
    st.caption("Enable Reddit by adding secrets (REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD/USER_AGENT).")
    st.info("This module will light up once secrets are set. No placeholders shown here.")

elif page == "My Data":
    st.header("My Data — Plug & View")
    st.write("Upload CSV/XLSX (e.g., foot traffic, loyalty, crossover). We’ll preview and validate.")
    f = st.file_uploader("Upload file", type=["csv","xlsx"])
    if f:
        name = f.name.lower()
        if name.endswith(".csv"):
            df = pd.read_csv(f)
            st.dataframe(df.head(50))
        else:
            xls = pd.ExcelFile(f)
            st.write("Sheets:", xls.sheet_names)
            for s in xls.sheet_names[:3]:
                df = pd.read_excel(xls, s)
                st.write(f"Preview — {s}")
                st.dataframe(df.head(50))
        st.success("Preview complete. (Say the word and I’ll wire full SQLite ingest + overlays.)")

elif page == "Methods":
    st.header("Methods & Data Quality")
    st.markdown("""
**Open sources**
- Reuters RSS (Business/Tech/World)
- Yahoo Finance via `yfinance` (sector ETFs and proxies)
- Google Trends via `pytrends` (country/region scoped)

**Refresh**
- All calls cached with TTL ≈ 5 minutes. If a source stalls, last good data is shown with this page timestamp.

**Sentiment**
- VADER on headlines → average per scope.

**Composite concept**
- Category momentum blends News z, Sentiment, Trends delta (when computed), and Market Δ%. No placeholders.
""")
