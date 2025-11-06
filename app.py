import os
import pandas as pd
import streamlit as st

from src.collectors import NewsCollector, GovCollector, MacroCollector, TrendsCollector, MobilityCollector, StocksCollector, SocialCollector
from src.analytics import aggregate_category_metrics, build_kpi_cards, category_market_trends_table
from src.emotions import score_sentiment_batch
from src.entities import extract_entities_batch
from src.narratives import cluster_topics
from src.theming import inject_css
from src.exporters import export_dataframe_csv
from src.risk_model import compute_risk_index
from src.ui_us import render_command_center, render_category_page, render_sources_sidebar
from src.store import cache_df

st.set_page_config(page_title="Intelligence Hub — US", page_icon=None, layout="wide")
inject_css()

st.sidebar.title("Intelligence Hub — US")
categories = ["Macro", "Technology", "Consumer", "Energy", "Healthcare", "Finance", "Retail", "Autos"]
selected_cats = st.sidebar.multiselect("Categories", categories, default=["Macro","Technology","Consumer"])
lookback_days = st.sidebar.slider("Lookback (days)", 1, 14, 3)
max_items = st.sidebar.slider("Max stories per source", 20, 200, 80, step=10)
st.sidebar.markdown("---")
with st.sidebar.expander("Sources"):
    render_sources_sidebar()
st.sidebar.markdown("---")
st.sidebar.caption("All data from public/free sources. Updated on load.")

# Collect
with st.spinner("Collecting live signals..."):
    news = NewsCollector().collect(selected_cats, max_items=max_items, lookback_days=lookback_days)
    gov = GovCollector().collect(max_items=120, lookback_days=lookback_days)
    social = SocialCollector().collect(selected_cats, max_items=120, lookback_days=lookback_days)
    macro = MacroCollector().collect(lookback_days=lookback_days)
    trends = TrendsCollector().collect(selected_cats, lookback_days=30)
    mobility = MobilityCollector().collect()
    stocks = StocksCollector().collect(["^GSPC","^IXIC","^DJI","AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA"])
    cat_mt = category_market_trends_table(lookback_days=7)  # << new robust signals

# Sentiment & Entities
all_text = pd.concat([news["title"], social["title"].fillna("")], axis=0).astype(str).tolist()
sent_df = score_sentiment_batch(all_text)
ent_df = extract_entities_batch(all_text)

# Narratives
topics = cluster_topics(pd.DataFrame({"text": all_text}))

# Merge per-item sentiment back into tables
news = news.copy()
news["sentiment"] = score_sentiment_batch(news["title"].astype(str))["compound"].values
social["sentiment"] = score_sentiment_batch(social["title"].astype(str))["compound"].values

# Aggregates & Risk
kpis = aggregate_category_metrics(news, social, trends, stocks)
risk = compute_risk_index(news, social, trends, stocks)

# Persist snapshots
cache_df("news", news); cache_df("gov", gov); cache_df("social", social)
cache_df("macro", macro); cache_df("trends", trends); cache_df("mobility", mobility); cache_df("stocks", stocks)

# UI
tabs = st.tabs(["Command Center", "Categories", "Market & Mobility", "Sources & Logs"])
with tabs[0]:
    render_command_center(kpis, risk, news, trends, stocks, mobility, ent_df, topics, cat_mt)

with tabs[1]:
    render_category_page(selected_cats, news, social, trends, ent_df, topics)

with tabs[2]:
    c1, c2 = st.columns((1,1))
    with c1:
        st.subheader("Market Overview")
        st.dataframe(stocks, use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Mobility")
        st.dataframe(mobility, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Government & Regulatory Feed")
    st.dataframe(gov, use_container_width=True, hide_index=True)
    st.subheader("Macro Indicators")
    st.dataframe(macro, use_container_width=True, hide_index=True)

st.sidebar.download_button("Download News CSV", export_dataframe_csv(news), file_name="news.csv", mime="text/csv")
