# app.py  (REPLACE FILE)

import pandas as pd
import streamlit as st
import plotly.express as px
from dateutil import tz
from datetime import datetime
import yfinance as yf


from src.theming import inject_css, kpi
from src.collectors import (
    REGIONS, TOP_MARKETS, CATEGORIES,
    fetch_news, fetch_quotes, fetch_trends,
    news_z_dynamic, senti_avg, ccs_simple, estimated_feed_size
)

st.set_page_config(page_title="Intelligence Hub", page_icon=None, layout="wide")
inject_css()
IST = tz.gettz("Asia/Kolkata")

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
    return (None if region=="—" else region), (None if country=="—" else country)

def category_select():
    return st.selectbox("Category", list(CATEGORIES.keys()), format_func=lambda k: CATEGORIES[k]["name"])

@st.cache_data(ttl=300, show_spinner=False)
def _news(cat, country, region): return fetch_news(cat, country, region)

@st.cache_data(ttl=300, show_spinner=False)
def _quotes(symbols): return fetch_quotes(symbols)

@st.cache_data(ttl=300, show_spinner=False)
def _trends(cat, geo): return fetch_trends(cat, geo)

# ---------- COMMAND CENTER ----------
if page == "Command Center":
    st.header("Command Center")
    st.caption("Global pulse across categories. Real open data only.")

    # KPI trio from Technology (good signal density)
    feed_n = estimated_feed_size()
    tech_news = _news("technology", None, None)
    nz = news_z_dynamic(tech_news, feed_n)
    sa = senti_avg(tech_news)
    q = _quotes(CATEGORIES["technology"]["tickers"])
    mkt = (q[0]["pct"] if q else 0.0)

    c1,c2,c3 = st.columns(3)
    with c1: kpi("Composite (Tech)", f"{ccs_simple(nz, sa, None, mkt):.2f}")
    with c2: kpi("Sentiment (Tech)", f"{sa:.2f}", "VADER avg on Reuters titles")
    with c3: kpi("News volume z (Tech)", f"{nz:.2f}", f"Baseline from feed size ≈ {feed_n}")

    # Category table
    st.subheader("Category Heatmap (24–72h)")
    rows = []
    for slug, cfg in CATEGORIES.items():
        news = _news(slug, None, None)
        q2 = _quotes(cfg["tickers"])
        rows.append({
            "Category": cfg["name"],
            "News z": news_z_dynamic(news, feed_n),
            "Sentiment": senti_avg(news),
            "Market Δ%": q2[0]["pct"] if q2 else 0.0
        })
    st.dataframe(pd.DataFrame(rows).set_index("Category"))

    st.subheader("Top Storylines (Reuters)")
    for slug, cfg in CATEGORIES.items():
        st.markdown(f"**{cfg['name']}**")
        items = _news(slug, None, None)[:6]
        if not items:
            st.markdown('<span class="muted">No matching headlines right now.</span>', unsafe_allow_html=True)
            continue
        for h in items:
            st.write(f"- [{h['title']}]({h['link']}) — {h['published']} · Sentiment {h['senti']:.2f}")

# ---------- REGIONS ----------
elif page == "Regions":
    st.header("Regions")
    region, country = region_country_controls()
    cat = category_select()

    feed_n = estimated_feed_size()
    left, right = st.columns([1.25, 0.75])

    with left:
        st.subheader("News & Sentiment")
        headlines = _news(cat, country, region)
        if headlines:
            df = pd.DataFrame(headlines)[["title","source","published","senti","link"]]
            st.dataframe(df, hide_index=True)
        nz = news_z_dynamic(headlines, feed_n)
        sa = senti_avg(headlines)
        st.caption(f"News z: {nz:.2f} • Sentiment: {sa:.2f}")

    with right:
        st.subheader("Market Pulse")
        q = _quotes(CATEGORIES[cat]["tickers"])
        if q:
            dfq = pd.DataFrame(q)
            st.dataframe(dfq, hide_index=True)
            # simple sparkline
            try:
                sym = dfq["symbol"].iloc[0]
                hist = pd.DataFrame(yf.Ticker(sym).history(period="1mo")["Close"]).reset_index()
                fig = px.line(hist, x="Date", y="Close")
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                pass

        st.subheader("Search Interest (90 days)")
        geo = country or region or "IN"
        try:
            ts = _trends(cat, geo)
            for d in ts["datasets"]:
                fig = px.line(pd.DataFrame({"date": ts["labels"], d["label"]: d["data"]}), x="date", y=d["label"])
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.markdown('<span class="muted">Trends not available for this scope right now.</span>', unsafe_allow_html=True)

# ---------- CATEGORIES ----------
elif page == "Categories":
    st.header("Categories")
    region, country = region_country_controls()
    cat = category_select()

    feed_n = estimated_feed_size()
    headlines = _news(cat, country, region)
    nz = news_z_dynamic(headlines, feed_n)
    sa = senti_avg(headlines)
    q = _quotes(CATEGORIES[cat]["tickers"]); pct = q[0]["pct"] if q else 0.0

    c1,c2,c3 = st.columns(3)
    with c1: kpi("News z", f"{nz:.2f}")
    with c2: kpi("Sentiment", f"{sa:.2f}")
    with c3: kpi("Market Δ%", f"{pct:.2f}%")

    st.subheader("News")
    if headlines:
        st.dataframe(pd.DataFrame(headlines)[["title","source","published","senti","link"]], hide_index=True)
    else:
        st.markdown('<span class="muted">No matching stories right now.</span>', unsafe_allow_html=True)

    st.subheader("Trends (90 days)")
    geo = country or region or "IN"
    try:
        ts = _trends(cat, geo)
        for d in ts["datasets"]:
            fig = px.line(pd.DataFrame({"date": ts["labels"], d["label"]: d["data"]}), x="date", y=d["label"])
            st.plotly_chart(fig, use_container_width=True)
    except Exception:
        st.markdown('<span class="muted">Trends not available for this scope right now.</span>', unsafe_allow_html=True)

# ---------- MARKETS ----------
elif page == "Markets":
    st.header("Markets & Media Conditions")
    rows=[]
    for slug,cfg in CATEGORIES.items():
        q = _quotes(cfg["tickers"])
        if q: rows.extend(q)
    if rows:
        st.dataframe(pd.DataFrame(rows).drop_duplicates(subset=["symbol"]).set_index("symbol"))
    st.caption("Add FX/commodities (EURUSD, GBPUSD, USDJPY, USDINR, Brent, Gold) later via yfinance tickers.")

# ---------- SOCIAL ----------
elif page == "Social":
    st.header("Social & Community Pulse")
    st.caption("Enable Reddit by setting REDDIT_* secrets. UI intentionally empty without credentials (no placeholders).")

# ---------- MY DATA ----------
elif page == "My Data":
    st.header("My Data — Plug & View")
    f = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx"])
    if f:
        name=f.name.lower()
        if name.endswith(".csv"):
            df=pd.read_csv(f); st.dataframe(df.head(50))
        else:
            xls=pd.ExcelFile(f); st.write("Sheets:", xls.sheet_names)
            for s in xls.sheet_names[:3]:
                df=pd.read_excel(xls,s); st.write(f"Preview — {s}"); st.dataframe(df.head(50))
        st.success("Preview complete. (Say “add ingest” and I’ll wire SQLite storage + overlays.)")

# ---------- METHODS ----------
else:
    st.header("Methods & Data Quality")
    st.markdown("""
**Open sources**: Reuters RSS, Yahoo Finance (`yfinance`), Google Trends (`pytrends`).  
**Refresh**: cache TTL ≈ 5 minutes; last good values shown with timestamp.  
**Sentiment**: VADER on Reuters titles.  
**News z**: dynamic baseline derived from current feed size (no hard-coded constants).  
""")
