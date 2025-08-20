# Intelligence Hub — Streamlit (Render-ready, real-data only)
# Quiet luxury: minimal, fast, and reliable. No placeholders.

import os
import time
import pandas as pd
import streamlit as st

from src.data_sources import (
    fetch_market_snapshot,
    fetch_rss_bundle,
    compute_sentiment,
    fetch_google_trends,
    fetch_opensky_air_traffic,
    fetch_reddit_posts_if_configured
)
from src.ui import (
    markets_block,
    news_block,
    trends_block,
    mobility_block,
    reddit_block
)
from src.theming import apply_page_style

st.set_page_config(
    page_title="Intelligence Hub",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_page_style()

st.markdown("### Intelligence Hub")
st.caption("Real data. Executive-grade. No fluff.")

# Sidebar controls (kept concise; everything has safe defaults)
with st.sidebar:
    st.markdown("#### Controls")
    tickers = st.text_input(
        "Tickers (comma-separated)",
        value=os.getenv("DEFAULT_TICKERS", "RELIANCE.NS,TCS.NS,INFY.NS,^NSEI,TSLA,AAPL,MSFT")
    )
    gdelt_topics = st.text_input(
        "News topics (comma-separated)",
        value=os.getenv("DEFAULT_TOPICS", "india economy, ad tech, mobility, inflation, retail")
    )
    rss_bundle = st.selectbox(
        "News bundle",
        options=["world_major", "business_tech"],
        index=0
    )
    st.caption("Optional APIs enabled via environment variables on Render:")
    st.code("REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT\nOPENSKY_USERNAME, OPENSKY_PASSWORD", language="bash")

st.markdown("---")

# MARKETS
with st.container():
    st.subheader("Markets")
    tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
    mdf = fetch_market_snapshot(tickers_list)
    markets_block(mdf)

st.markdown("---")

# NEWS + SENTIMENT (RSS only, no keys needed)
with st.container():
    st.subheader("News & Sentiment")
    articles = fetch_rss_bundle(rss_bundle)
    sdf = compute_sentiment(articles)
    news_block(sdf)

st.markdown("---")

# GOOGLE TRENDS (no key)
with st.container():
    st.subheader("Google Trends — Rising Queries")
    topics = [t.strip() for t in gdelt_topics.split(",") if t.strip()]
    tdf = fetch_google_trends(topics)
    trends_block(tdf)

st.markdown("---")

# MOBILITY (OpenSky anonymous or account — real data only)
with st.container():
    st.subheader("Air Mobility Signal (OpenSky Network)")
    try:
        adf = fetch_opensky_air_traffic()
        mobility_block(adf)
    except Exception as e:
        st.info("OpenSky rate-limited or unavailable at the moment.")
        st.caption(str(e))

st.markdown("---")

# REDDIT (optional; shown only if env vars set)
with st.container():
    st.subheader("Reddit Signal (optional)")
    rdf = fetch_reddit_posts_if_configured(["economy", "geopolitics", "advertising", "marketing"])
    reddit_block(rdf)

st.caption("© Intelligence Hub")
