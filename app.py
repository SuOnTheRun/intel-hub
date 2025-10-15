import streamlit as st
import pandas as pd
from src.collectors import get_news_dataframe
from src.emotions import add_sentiment
from src.data_sources import category_metrics
from src.analytics import build_category_heatmap, headline_blocks
from src.ui import kpi_cards, heatmap, headlines_section

st.set_page_config(page_title="Intelligence Hub", layout="wide")

st.sidebar.title("Intelligence Hub")
st.sidebar.radio(" ", ["Command Center","Regions","Categories","Markets","Social","My Data","Methods"], index=0)
st.sidebar.caption(f"Updated: {pd.Timestamp.utcnow().tz_localize('UTC').tz_convert('Asia/Kolkata').strftime('%d %b %Y, %H:%M IST')}")

st.title("Command Center")
st.caption("Global pulse across categories from BBC / Al Jazeera / Reuters / DW / Google News RSS; markets via Yahoo Finance; trends via Google Trends.")

# --- DATA ---
news_df = get_news_dataframe("src/news_rss_catalog.json")
news_df = add_sentiment(news_df)

base = category_metrics()
heat = build_category_heatmap(news_df, base)

# --- UI ---
kpi_cards(heat)
st.subheader("Category Heatmap (24–72h)")
heatmap(heat)

blocks = headline_blocks(news_df, by_category=True, top_n=8)
headlines_section(blocks)
