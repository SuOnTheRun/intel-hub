import os
import streamlit as st
import pandas as pd

from src.theming import apply_page_style
from src.presets import region_names, region_bbox, region_center
from src.analytics import (
    enrich_news_with_topics_regions, aggregate_kpis, build_social_listening_panels,
    add_risk_scores, filter_by_controls, TOPIC_LIST,
)
from src.data_sources import (
    fetch_market_snapshot, fetch_rss_bundle, fetch_newsapi_bundle, merge_news_and_dedupe,
    fetch_google_trends, fetch_opensky_air_traffic, fetch_opensky_tracks_for_icao24,
    fetch_reddit_posts_if_configured, fetch_gdelt_events,
)
from src.maps import render_global_air_map, render_tracks_map
from src.ui import (
    render_header, render_kpi_row, render_event_cards, render_news_table, render_markets,
    render_trends, render_reddit, render_regions_grid, render_feed_panel,
)
from src.exporters import download_buttons

st.set_page_config(page_title="Strategic Intelligence War Room", layout="wide", initial_sidebar_state="collapsed")
apply_page_style()
render_header()

# ---------------- Sidebar Filters ----------------
with st.sidebar:
    st.markdown("#### Filters")
    region = st.selectbox("Region preset", options=region_names(), index=region_names().index("Indo-Pacific"))
    hours = st.slider("Time window (hours)", min_value=6, max_value=96, value=48, step=6)
    topics = st.multiselect("Topics", options=TOPIC_LIST, default=["Security","Mobility","Markets","Elections"])
    tickers = st.text_input("Tickers (comma-separated)", value=os.getenv("DEFAULT_TICKERS","RELIANCE.NS,TCS.NS,INFY.NS,^NSEI,TSLA,AAPL,MSFT"))
    rss_bundle = st.selectbox("RSS bundle", options=["world_major","business_tech"], index=0)
    widen_air = st.checkbox("Fallback to global air traffic when region is quiet", value=True)
    st.caption("Optional APIs via Render env vars: NEWSAPI_KEY · POLYGON_ACCESS_KEY · REDDIT_* · OPENSKY_*")

# ---------------- Data Pulls ----------------
tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
markets_df = fetch_market_snapshot(tickers_list)

rss_df = fetch_rss_bundle(rss_bundle)
newsapi_df = fetch_newsapi_bundle([region] + topics)  # bias NewsAPI to region/topic terms
news_df_raw = merge_news_and_dedupe(rss_df, newsapi_df)

news_df = enrich_news_with_topics_regions(news_df_raw)
news_df = add_risk_scores(news_df)
news_df = filter_by_controls(news_df, region=region, topics=topics, hours=hours)

gdelt_df = fetch_gdelt_events([region] + topics)
if not gdelt_df.empty:
    gdelt_df = enrich_news_with_topics_regions(gdelt_df)
    gdelt_df = add_risk_scores(gdelt_df)
    gdelt_df = filter_by_controls(gdelt_df, region=region, topics=topics, hours=hours)

trends_df = fetch_google_trends(topics)

bbox = region_bbox(region)
try:
    air_df = fetch_opensky_air_traffic(bbox=bbox, allow_global_fallback=widen_air)
except Exception:
    air_df = pd.DataFrame()

reddit_df = fetch_reddit_posts_if_configured(["economy","geopolitics","advertising","marketing"])
social_panels = build_social_listening_panels(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, reddit_df)

kpis = aggregate_kpis(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, gdelt_df, air_df)
download_buttons(news_df=news_df, gdelt_df=gdelt_df, markets_df=markets_df, air_df=air_df, trends_df=trends_df, reddit_df=reddit_df)

# ---------------- Tabs ----------------
tab_overview, tab_regions, tab_feed, tab_mobility, tab_markets, tab_social = st.tabs(
    ["Overview","Regional Analysis","Intelligence Feed","Movement Tracking","Markets","Social Listening"]
)

with tab_overview:
    render_kpi_row(kpis)
    render_event_cards(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, "Top Events", n=12)
    st.markdown("##### Global Intelligence Map")
    render_global_air_map(air_df, center=region_center(region), zoom=4)

with tab_regions:
    render_regions_grid(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, expanded=True)

with tab_feed:
    render_feed_panel(news_df, gdelt_df)

with tab_mobility:
    st.markdown("##### Live Air Traffic")
    render_global_air_map(air_df, center=region_center(region), zoom=5)
    if not air_df.empty and "icao24" in air_df.columns:
        icao24s = sorted(air_df["icao24"].dropna().unique().tolist())
        if icao24s:
            selected = st.selectbox("Select ICAO24 for recent track (requires OpenSky auth)", icao24s)
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
