# app.py — Intelligence Hub (routing + upgraded Command Center)

import os, sys
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# Make ./src importable even if package path differs on host
SRC_DIR = os.path.join(os.path.dirname(__file__), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Viewer timezone (browser)
try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None

# Imports (package → fallback-to-module)
try:
    from src.collectors import get_news_dataframe
    from src.emotions import add_sentiment
    from src.data_sources import category_metrics
    from src.analytics import build_category_heatmap, headline_blocks
    from src.narratives import build_narratives
    from src.entities import extract_entities
    from src.risk_model import compute_tension
    from src.ui import (
        luxe_header, kpi_ribbon, heatmap_labeled, headlines_overview,
        narratives_panel, tension_panel, sentiment_explainer, glossary_panel
    )
except Exception:
    from collectors import get_news_dataframe
    from emotions import add_sentiment
    from data_sources import category_metrics
    from analytics import build_category_heatmap, headline_blocks
    from narratives import build_narratives
    from entities import extract_entities
    from risk_model import compute_tension
    from ui import (
        luxe_header, kpi_ribbon, heatmap_labeled, headlines_overview,
        narratives_panel, tension_panel, sentiment_explainer, glossary_panel
    )

# ---------- Page config ----------
st.set_page_config(page_title="Intelligence Hub", layout="wide", initial_sidebar_state="expanded")

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

@st.cache_data(ttl=15 * 60, show_spinner=False)
def load_news_df(catalog_path: str) -> pd.DataFrame:
    df = get_news_dataframe(catalog_path)
    df = add_sentiment(df)
    return df

@st.cache_data(ttl=10 * 60, show_spinner=False)
def load_category_metrics() -> pd.DataFrame:
    return category_metrics()

# ---------- Sidebar & routing ----------
st.sidebar.title("Intelligence Hub")
page = st.sidebar.radio(
    " ",
    ["Command Center", "Regions", "Categories", "Markets", "Social", "My Data", "Methods"],
    index=0
)
st.sidebar.caption(f"Updated: {get_viewer_now().strftime('%d %b %Y, %H:%M %Z')}")

# Preload data once (used by multiple pages)
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

# ---------- ROUTES ----------
if page == "Command Center":
    # Polished header
    luxe_header(
        title="Command Center",
        subtitle="A live situational read on markets, narratives, and public interest, distilled for decision-making."
    )

    # KPIs (now intuitive & comprehensive) + glossary tooltip
    # Merge Tension for ribbon
    with st.spinner("Computing HUMINT layers…"):
        ent_df = extract_entities(news_df, top_n=8)
        tension_df = compute_tension(news_df, heat, ent_df)

    kpi_ribbon(heat_df=heat, tension_df=tension_df)

    # Labeled heatmap with micro-instructions
    st.subheader("Category Heatmap (24–72h)")
    heatmap_labeled(heat)
    st.caption("Note: Hover to inspect values. Drag to zoom; double-click to reset view.")

    # Sentiment interpretation (plain English)
    sentiment_explainer(heat, news_df)

    st.markdown("---")

    # Narratives & Entities
    st.header("HUMINT Deep-Dive")
    with st.spinner("Deriving narratives…"):
        narr = build_narratives(news_df, top_n=3)
    narratives_panel(narr.table, narr.top_docs_by_cat)

    st.subheader("Prominent Entities (ORG / PERSON / GPE)")
    if ent_df.empty:
        st.caption("No entities extracted.")
    else:
        st.dataframe(ent_df, use_container_width=True)

    # Tension Index table
    tension_panel(tension_df)

    # Headlines — now *overviewed* and paged/filterable
    st.markdown("---")
    st.header("Top Headlines by Category")
    headlines_overview(news_df)

    # At the bottom: quick glossary
    st.markdown("---")
    glossary_panel()

elif page == "Categories":
    luxe_header("Categories", "Drilldowns by industry vertical.")
    # Quick selector and table
    cats = sorted(heat["category"].unique().tolist()) if not heat.empty else []
    sel = st.selectbox("Choose a category", cats) if cats else None
    if sel:
        sub = news_df[news_df["category"] == sel].sort_values("published_dt", ascending=False)
        st.write(f"Latest in **{sel}**")
        st.dataframe(sub[["published_dt","source","title","link","sentiment"]].head(200), use_container_width=True)
    else:
        st.info("No categories available yet.")

elif page == "Markets":
    luxe_header("Markets", "Five-day % change by mapped proxies; use Command Center for context.")
    st.dataframe(heat[["category","market_pct","news_count","trends","sentiment","composite"]], use_container_width=True)

elif page == "Regions":
    luxe_header("Regions", "Regional view coming next: geospatial layers & movement tracking (Milestone 2).")
    st.info("Regional OSINT/HUMINT and mobility layers will land in Milestone 2.")

elif page == "Social":
    luxe_header("Social", "Community pulse via Reddit and trend signals (Milestone 2).")
    st.info("Reddit HUMINT and topic velocity will land in Milestone 2.")

elif page == "My Data":
    luxe_header("My Data", "Bring your own sheets/logs for private overlays.")
    st.info("Uploads & overlays to be enabled after snapshots module (Milestone 3–4).")

elif page == "Methods":
    luxe_header("Methods", "How metrics are computed.")
    glossary_panel(show_full=True)
