# STRATEGIC INTELLIGENCE WAR ROOM — Executive Edition
# Ultra‑clean layout, tabs, scorecards, real sources only.

import os
import streamlit as st
import pandas as pd

from src.theming import apply_page_style
from src.analytics import (
    enrich_news_with_topics_regions,
    aggregate_kpis,
    build_social_listening_panels,
)
from src.data_sources import (
    fetch_market_snapshot,
    fetch_rss_bundle,
    fetch_newsapi_bundle,
    merge_news_and_dedupe,
    fetch_google_trends,
    fetch_opensky_air_traffic,
    fetch_opensky_tracks_for_icao24,
    fetch_reddit_posts_if_configured,
    fetch_gdelt_events,
)
from src.maps import render_global_air_map, render_tracks_map
from src.ui import (
    render_header,
    render_kpi_row,
    render_news_table,
    render_markets,
    render_trends,
    render_reddit,
    render_regions_grid,
    render_feed_panel,
)
from src.exporters import download_buttons

# --------------------------------------------------------------------------------------
# PAGE SETUP
# --------------------------------------------------------------------------------------
st.set_page_config(page_title="Strategic Intelligence War Room", layout="wide", initial_sidebar_state="collapsed")
apply_page_style()
render_header()

# --------------------------------------------------------------------------------------
# SIDEBAR CONTROLS
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.markdown("#### Controls")
    tickers = st.text_input(
        "Tickers (comma‑separated)",
        value=os.getenv("DEFAULT_TICKERS", "RELIANCE.NS,TCS.NS,INFY.NS,^NSEI,TSLA,AAPL,MSFT")
    )
    queries_str = st.text_input(
        "Focus topics (comma‑separated)",
        value=os.getenv("DEFAULT_TOPICS", "india economy, ad tech, mobility, inflation, retail, elections, conflict")
    )
    rss_bundle = st.selectbox("RSS bundle", options=["world_major", "business_tech"], index=0)
    bbox = st.text_input("Air‑traffic bbox (minLat,minLon,maxLat,maxLon)", value="5,60,35,100")
    st.caption("Optional APIs via environment variables:")
    st.code("NEWSAPI_KEY | POLYGON_ACCESS_KEY\nREDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT\nOPENSKY_USERNAME, OPENSKY_PASSWORD", language="bash")

topics = [x.strip() for x in queries_str.split(",") if x.strip()]
tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]

# --------------------------------------------------------------------------------------
# DATA PULLS
# --------------------------------------------------------------------------------------
# Markets (Polygon if available else Yahoo)
markets_df = fetch_market_snapshot(tickers_list)

# News (RSS + NewsAPI) → merged → topic/region enrichment
rss_df = fetch_rss_bundle(rss_bundle)
newsapi_df = fetch_newsapi_bundle(topics)
news_df_raw = merge_news_and_dedupe(rss_df, newsapi_df)
news_df = enrich_news_with_topics_regions(news_df_raw)

# GDELT events (adds geopolitically‑tagged items; no key)
gdelt_df = fetch_gdelt_events(topics)
if not gdelt_df.empty:
    gdelt_df = enrich_news_with_topics_regions(gdelt_df)

# Google Trends
trends_df = fetch_google_trends(topics)

# Air positions (OpenSky)
try:
    air_df = fetch_opensky_air_traffic(bbox=bbox)
except Exception:
    air_df = pd.DataFrame()

# Reddit (optional via env)
reddit_df = fetch_reddit_posts_if_configured(["economy", "geopolitics", "advertising", "marketing"])

# Social listening panels from News + Reddit
social_panels = build_social_listening_panels(news_df, reddit_df)

# KPIs
kpis = aggregate_kpis(news_df, gdelt_df, air_df)

# --------------------------------------------------------------------------------------
# EXPORTS (download buttons collect all major frames)
# --------------------------------------------------------------------------------------
download_buttons(
    news_df=news_df,
    gdelt_df=gdelt_df,
    markets_df=markets_df,
    air_df=air_df,
    trends_df=trends_df,
    reddit_df=reddit_df,
)

# --------------------------------------------------------------------------------------
# TABS
# --------------------------------------------------------------------------------------
tab_overview, tab_regions, tab_feed, tab_mobility, tab_markets, tab_social = st.tabs(
    ["Overview", "Regional Analysis", "Intelligence Feed", "Movement Tracking", "Markets", "Social Listening"]
)

with tab_overview:
    render_kpi_row(kpis)
    st.markdown("##### Global Intelligence Map")
    render_global_air_map(air_df)
    st.markdown("##### Executive Summary")
    render_regions_grid(news_df)  # concise cards by region/topic

with tab_regions:
    render_regions_grid(news_df, expanded=True)

with tab_feed:
    render_feed_panel(news_df, gdelt_df)

with tab_mobility:
    st.markdown("##### Live Air Traffic")
    render_global_air_map(air_df)
    if not air_df.empty:
        # Let user select an aircraft to load recent track (if OpenSky creds exist, this works; otherwise it will inform)
        callsigns = air_df["callsign"].dropna().unique().tolist()
        icao24s = air_df["icao24"].dropna().unique().tolist()
        selected = st.selectbox("Select ICAO24 for track (sorted)", sorted(icao24s))
        if selected:
            tdf = fetch_opensky_tracks_for_icao24(selected)
            render_tracks_map(tdf)

with tab_markets:
    render_markets(markets_df)
    render_trends(trends_df)

with tab_social:
    render_reddit(reddit_df)
    for block in social_panels:
        st.markdown(f"#### {block['title']}")
        st.dataframe(block["table"], use_container_width=True, height=360)
