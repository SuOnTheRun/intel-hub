# app.py — Intelligence Hub (OSINT + HUMINT)
# Full Streamlit entrypoint with viewer-timezone detection

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# Browser timezone detection (no IP lookups)
try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None

# --- Project modules ---
from src.collectors import get_news_dataframe
from src.emotions import add_sentiment
from src.data_sources import category_metrics
from src.analytics import build_category_heatmap, headline_blocks
from src.ui import kpi_cards, heatmap, headlines_section

# -----------------------------
# Page configuration
# -----------------------------
st.set_page_config(
    page_title="Intelligence Hub",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Utilities
# -----------------------------
def get_viewer_now():
    """
    Returns current datetime in the viewer's local timezone.
    Uses browser's Intl API via streamlit_javascript; falls back to Asia/Kolkata.
    """
    tz_fallback = "Asia/Kolkata"
    tz_name = None
    if st_javascript is not None:
        try:
            tz_name = st_javascript("Intl.DateTimeFormat().resolvedOptions().timeZone")
        except Exception:
            tz_name = None
    if not tz_name:
        tz_name = tz_fallback
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(tz_fallback)
    return datetime.now(tz)

@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_news_df(catalog_path: str) -> pd.DataFrame:
    df = get_news_dataframe(catalog_path)
    df = add_sentiment(df)
    return df

@st.cache_data(ttl=10 * 60, show_spinner=False)
def load_category_metrics() -> pd.DataFrame:
    return category_metrics()

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Intelligence Hub")
_ = st.sidebar.radio(" ", ["Command Center", "Regions", "Categories", "Markets", "Social", "My Data", "Methods"], index=0)
now_local = get_viewer_now()
st.sidebar.caption(f"Updated: {now_local.strftime('%d %b %Y, %H:%M %Z')}")

# -----------------------------
# Header
# -----------------------------
st.title("Command Center")
st.caption(
    "Global pulse across categories from BBC / Al Jazeera / Reuters / DW / Google News RSS; "
    "markets via Yahoo Finance; trends via Google Trends."
)

# -----------------------------
# Data section
# -----------------------------
with st.spinner("Fetching live signals…"):
    try:
        news_df = load_news_df("src/news_rss_catalog.json")
    except Exception as e:
        st.error(f"News feed error: {e}")
        news_df = pd.DataFrame(columns=["category","title","link","published","summary","source","published_dt","sentiment"])

    try:
        base = load_category_metrics()
    except Exception as e:
        st.error(f"Signals error: {e}")
        base = pd.DataFrame(columns=["category","trends","market_pct"])

    try:
        heat = build_category_heatmap(news_df, base)
    except Exception as e:
        st.error(f"Analytics error: {e}")
        heat = pd.DataFrame(columns=["category","news_z","sentiment","market_pct","composite","news_count","trends"])

# -----------------------------
# KPIs + Heatmap
# -----------------------------
if not heat.empty:
    kpi_cards(heat)
    st.subheader("Category Heatmap (24–72h)")
    heatmap(heat)
else:
    st.info("No category signals available yet. If this persists, check outbound access on your host and the RSS catalog file.")

# -----------------------------
# Headlines
# -----------------------------
blocks = headline_blocks(news_df, by_category=True, top_n=8)
headlines_section(blocks)

# -----------------------------
# Optional: raw data expanders
# -----------------------------
with st.expander("Raw: Category Signals"):
    st.dataframe(heat, use_container_width=True)

with st.expander("Raw: Latest Headlines"):
    st.dataframe(news_df[["category","published_dt","source","title","link","sentiment"]].head(200), use_container_width=True)


# app.py — Intelligence Hub with Milestone 1 modules

import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# Browser timezone detection
try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None

# Project modules
from src.collectors import get_news_dataframe
from src.emotions import add_sentiment
from src.data_sources import category_metrics
from src.analytics import build_category_heatmap, headline_blocks
from src.ui import kpi_cards, heatmap, headlines_section, narratives_panel, tension_panel
from src.narratives import build_narratives
from src.entities import extract_entities
from src.risk_model import compute_tension

# Page config
st.set_page_config(page_title="Intelligence Hub", layout="wide", initial_sidebar_state="expanded")

# Utilities
def get_viewer_now():
    tz_fallback = "Asia/Kolkata"
    tz_name = None
    if st_javascript is not None:
        try:
            tz_name = st_javascript("Intl.DateTimeFormat().resolvedOptions().timeZone")
        except Exception:
            tz_name = None
    if not tz_name:
        tz_name = tz_fallback
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo(tz_fallback)
    return datetime.now(tz)

@st.cache_data(ttl=15*60, show_spinner=False)
def load_news_df(path: str) -> pd.DataFrame:
    df = get_news_dataframe(path)
    df = add_sentiment(df)
    return df

@st.cache_data(ttl=10*60, show_spinner=False)
def load_category_metrics() -> pd.DataFrame:
    return category_metrics()

# Sidebar
st.sidebar.title("Intelligence Hub")
_ = st.sidebar.radio(" ", ["Command Center","Regions","Categories","Markets","Social","My Data","Methods"], index=0)
st.sidebar.caption(f"Updated: {get_viewer_now().strftime('%d %b %Y, %H:%M %Z')}")

# Header
st.title("Command Center")
st.caption("Live OSINT from BBC/Al Jazeera/Reuters/DW/Google News RSS; markets via Yahoo Finance; trends via Google Trends. Narratives, Entities, and a composite Tension Index enrich the HUMINT layer.")

# Data load
with st.spinner("Fetching live signals…"):
    news_df = load_news_df("src/news_rss_catalog.json")
    base = load_category_metrics()
    heat = build_category_heatmap(news_df, base)

# KPIs + Heatmap
if not heat.empty:
    kpi_cards(heat)
    st.subheader("Category Heatmap (24–72h)")
    heatmap(heat)
else:
    st.info("No category signals available yet.")

# Headlines
blocks = headline_blocks(news_df, by_category=True, top_n=8)
headlines_section(blocks)

# Milestone 1 — Narratives, Entities, Tension Index
st.markdown("---")
st.header("HUMINT Deep-Dive")

# 1) Narratives
with st.spinner("Deriving narratives…"):
    narr = build_narratives(news_df, top_n=3)
narratives_panel(narr.table, narr.top_docs_by_cat)

# 2) Entities
with st.spinner("Extracting entities…"):
    ent_df = extract_entities(news_df, top_n=8)
st.subheader("Prominent Entities (ORG/PERSON/GPE)")
if ent_df.empty:
    st.caption("No entities extracted.")
else:
    st.dataframe(ent_df, use_container_width=True)

# 3) Risk / Tension Index
with st.spinner("Computing Tension Index…"):
    tension_df = compute_tension(news_df, heat, ent_df)
tension_panel(tension_df)

# Expanders
with st.expander("Raw: Category Signals"):
    st.dataframe(heat, use_container_width=True)
with st.expander("Raw: Headlines"):
    st.dataframe(news_df[["category","published_dt","source","title","link","sentiment"]].head(300), use_container_width=True)
with st.expander("Raw: Entities"):
    st.dataframe(ent_df, use_container_width=True)
with st.expander("Raw: Tension Drivers"):
    st.dataframe(tension_df, use_container_width=True)

