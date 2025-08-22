import os
import streamlit as st
import pandas as pd

from src.theming import apply_page_style
from src.presets import region_names, region_bbox, region_center, region_keywords
from src.analytics import (
    enrich_news_with_topics_regions, aggregate_kpis, build_social_listening_panels,
    add_risk_scores, filter_by_controls, TOPIC_LIST, cluster_headlines,
    # NEW ↓
    add_emotions, extend_kpis_with_intel
)
from src.data_sources import (
    fetch_market_snapshot, fetch_rss_bundle, fetch_newsapi_bundle, merge_news_and_dedupe,
    fetch_google_trends, fetch_opensky_air_traffic, fetch_opensky_tracks_for_icao24,
    fetch_reddit_posts_if_configured, fetch_gdelt_events,
)
from src.maps import render_global_air_map, render_tracks_map
# later we will also call render_global_gdelt_map via local import in the tab
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
    rnames = region_names()
    default_idx = rnames.index("Indo-Pacific") if "Indo-Pacific" in rnames else 0
    region = st.selectbox("Region preset", options=rnames, index=default_idx)
    hours = st.slider("Time window (hours)", min_value=6, max_value=96, value=48, step=6)
    topics = st.multiselect("Topics", options=TOPIC_LIST, default=["Security","Mobility","Markets","Elections"])
    tickers = st.text_input("Tickers (comma-separated)", value=os.getenv("DEFAULT_TICKERS","RELIANCE.NS,TCS.NS,INFY.NS,^NSEI,TSLA,AAPL,MSFT"))
    rss_bundle = st.selectbox("RSS bundle", options=["world_major","business_tech"], index=0)
    widen_air = st.checkbox("Fallback to global air traffic when region is quiet", value=True)
    st.caption("APIs via env vars: NEWSAPI_KEY · POLYGON_ACCESS_KEY · REDDIT_* · OPENSKY_*")

# ---------------- Data Pulls ----------------
tickers_list = [t.strip() for t in tickers.split(",") if t.strip()]
markets_df = fetch_market_snapshot(tickers_list)

# Query strategy: region term + topics + region keywords (expands recall)
region_term = region
queries = [region_term] + topics + region_keywords(region)
rss_df = fetch_rss_bundle(rss_bundle)
newsapi_df = fetch_newsapi_bundle(queries)
news_df_raw = merge_news_and_dedupe(rss_df, newsapi_df)

# Enrich + risk + filter + cluster (auto-widen inside filter)
news_df = enrich_news_with_topics_regions(news_df_raw)
news_df = add_risk_scores(news_df)
news_df = filter_by_controls(news_df, region=region, topics=topics, hours=hours)
clustered = cluster_headlines(news_df, sim=72)

gdelt_df = fetch_gdelt_events(queries)
if not gdelt_df.empty:
    gdelt_df = enrich_news_with_topics_regions(gdelt_df)
    gdelt_df = add_risk_scores(gdelt_df)
    gdelt_df = filter_by_controls(gdelt_df, region=region, topics=topics, hours=hours)
    clustered_gdelt = cluster_headlines(gdelt_df, sim=72)
else:
    clustered_gdelt = pd.DataFrame()

# --- Emotion enrichment (row-level) ---
news_df = add_emotions(news_df)
if not gdelt_df.empty:
    gdelt_df = add_emotions(gdelt_df)


trends_df = fetch_google_trends(topics)
bbox = region_bbox(region)
try:
    air_df = fetch_opensky_air_traffic(bbox=bbox, allow_global_fallback=widen_air)
except Exception:
    air_df = pd.DataFrame()

reddit_df = fetch_reddit_posts_if_configured(["economy","geopolitics","advertising","marketing"])
social_panels = build_social_listening_panels(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, reddit_df)

# KPIs (existing) + extended intelligence KPIs
kpis = aggregate_kpis(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, gdelt_df, air_df)
kpis = extend_kpis_with_intel(kpis, news_df, gdelt_df if not gdelt_df.empty else None, air_df)
download_buttons(news_df=news_df, gdelt_df=gdelt_df, markets_df=markets_df, air_df=air_df, trends_df=trends_df, reddit_df=reddit_df)

with tab_overview:
    from src.ui import render_kpi_row_intel, render_event_cards_with_emotion
    render_kpi_row_intel(kpis)

    top_events = pd.concat([clustered, clustered_gdelt], ignore_index=True) if not clustered_gdelt.empty else clustered
    render_event_cards_with_emotion(top_events, "Top Events", n=12)

    st.markdown("##### Global Intelligence Map")
    from src.presets import region_center
    from src.maps import render_global_gdelt_map
    # Show risk/event heat on Overview; mobility map remains on Mobility tab
    render_global_gdelt_map(gdelt_df, center=region_center(region), zoom=4)


with tab_regions:
    render_regions_grid(pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df, expanded=True)

with tab_feed:
    render_feed_panel(news_df, gdelt_df)

with tab_mobility:
    st.markdown("##### Live Air Traffic")
    from src.presets import region_center
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
