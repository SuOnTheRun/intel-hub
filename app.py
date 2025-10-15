# app.py — Intelligence Hub (robust loader + upgraded Command Center)

import os, sys, importlib
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# ---------- Make ./src importable even if package path differs ----------
HERE = os.path.dirname(__file__)
SRC_DIR = os.path.join(HERE, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# ---------- Optional browser timezone ----------
try:
    from streamlit_javascript import st_javascript
except Exception:
    st_javascript = None

st.set_page_config(page_title="Intelligence Hub", layout="wide", initial_sidebar_state="expanded")

# ======================================================================
# Dynamic imports (prevents 502s if src/ package path differs on host)
# ======================================================================
def _try_import(module_name, alt_names=()):
    last_err = None
    for name in (module_name, *alt_names):
        try:
            return importlib.import_module(name)
        except Exception as e:
            last_err = e
    if last_err:
        raise last_err

try:
    collectors = _try_import("src.collectors", ("collectors",))
    emotions   = _try_import("src.emotions", ("emotions",))
    datasrc    = _try_import("src.data_sources", ("data_sources",))
    analytics  = _try_import("src.analytics", ("analytics",))
    narratives = _try_import("src.narratives", ("narratives",))
    entities   = _try_import("src.entities", ("entities",))
    riskmodel  = _try_import("src.risk_model", ("risk_model",))
    ui         = _try_import("src.ui", ("ui",))
except Exception as import_err:
    st.error("Startup import failed. Details below (this prevents a 502 so you can fix quickly).")
    st.exception(import_err)
    st.stop()

# ======================================================================
# Utilities
# ======================================================================
def get_viewer_now():
    """Return current datetime in viewer's local timezone via browser Intl API (fallback: Asia/Kolkata)."""
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
    df = collectors.get_news_dataframe(catalog_path)
    df = emotions.add_sentiment(df)  # uses VADER on lightweight build; auto-upgrades if transformers available later
    return df

@st.cache_data(ttl=10 * 60, show_spinner=False)
def load_category_metrics() -> pd.DataFrame:
    return datasrc.category_metrics()

# ======================================================================
# Sidebar & routing
# ======================================================================
st.sidebar.title("Intelligence Hub")
page = st.sidebar.radio(
    " ",
    ["Command Center", "Regions", "Categories", "Markets", "Social", "My Data", "Methods"],
    index=0,
)
st.sidebar.caption(f"Updated: {get_viewer_now().strftime('%d %b %Y, %H:%M %Z')}")

# ======================================================================
# Preload core data (shared across pages)
# ======================================================================
with st.spinner("Fetching live signals…"):
    try:
        news_df = load_news_df("src/news_rss_catalog.json")
    except Exception as e:
        st.error("News feed error — loaded empty frame to keep the app running.")
        news_df = pd.DataFrame(columns=["category","title","link","published","summary","source","published_dt","sentiment"])

    try:
        base = load_category_metrics()
    except Exception as e:
        st.error("Signals error — loaded empty frame to keep the app running.")
        base = pd.DataFrame(columns=["category","trends","market_pct"])

    try:
        heat = analytics.build_category_heatmap(news_df, base)
    except Exception as e:
        st.error("Analytics error — heatmap data unavailable.")
        heat = pd.DataFrame(columns=["category","news_z","sentiment","market_pct","composite","news_count","trends"])

# ======================================================================
# Routes
# ======================================================================
if page == "Command Center":
    ui.luxe_header(
        title="Command Center",
        subtitle="A live situational read on markets, narratives, and public interest, distilled for decision-making."
    )

    # HUMINT layers needed for KPIs and tables (silent fallbacks; no scary stack traces)
    with st.spinner("Computing HUMINT layers…"):
        try:
            ent_df = entities.extract_entities(news_df, top_n=8)
        except Exception:
            ent_df = pd.DataFrame(columns=["category","label","entity","count"])
        try:
            tension_df = riskmodel.compute_tension(news_df, heat, ent_df)
        except Exception:
            tension_df = pd.DataFrame(columns=["category","tension_0_100","neg_density","sent_vol","news_z","market_drawdown","trends_norm","entity_intensity"])

    # KPI ribbon (now uses headlines directly for Negativity % and Headline Tone)
    ui.kpi_ribbon(heat_df=heat, tension_df=tension_df, news_df=news_df)

    # Executive Highlights (Top momentum, highest tension, most negative, biggest move, interest spike)
    ui.highlights_panel(heat, tension_df)

    # Heatmap, labeled + micro-instructions
    st.subheader("Category Heatmap (24–72h)")
    ui.heatmap_labeled(heat)
    st.caption("Note: Hover to inspect values. Drag to zoom; double-click to reset view.")

    # Plain-English sentiment explainer for non-quant users
    ui.sentiment_explainer(heat, news_df)

    st.markdown("---")
    st.header("HUMINT Deep-Dive")

    # Narratives (with graceful fallback handled inside module)
    with st.spinner("Deriving narratives…"):
        try:
            narr = narratives.build_narratives(news_df, top_n=3)
        except Exception:
            from types import SimpleNamespace
            narr = SimpleNamespace(table=pd.DataFrame(columns=["category","narrative","weight","n_docs"]), top_docs_by_cat={})
    ui.narratives_panel(narr.table, narr.top_docs_by_cat)

    # Entities table
    st.subheader("Prominent Entities (ORG / PERSON / GPE)")
    if 'ent_df' in locals() and not ent_df.empty:
        st.dataframe(ent_df, use_container_width=True)
    else:
        st.caption("No entities extracted.")

    # Tension Index table
    ui.tension_panel(tension_df)

    # Headlines overview (paged + filterable)
    st.markdown("---")
    st.header("Top Headlines by Category")
    ui.headlines_overview(news_df)

    # Glossary
    st.markdown("---")
    ui.glossary_panel()

elif page == "Categories":
    ui.luxe_header("Categories", "Drilldowns by industry vertical.")
    cats = sorted(heat["category"].unique().tolist()) if not heat.empty else []
    sel = st.selectbox("Choose a category", cats) if cats else None
    if sel:
        sub = news_df[news_df["category"] == sel].sort_values("published_dt", ascending=False)
        st.write(f"Latest in **{sel}**")
        st.dataframe(sub[["published_dt","source","title","link","sentiment"]].head(200), use_container_width=True)
    else:
        st.info("No categories available yet.")

elif page == "Markets":
    ui.luxe_header("Markets", "Five-day % change by mapped proxies; use Command Center for context.")
    st.dataframe(heat[["category","market_pct","news_count","trends","sentiment","composite"]], use_container_width=True)

elif page == "Regions":
    ui.luxe_header("Regions", "Regional view coming next: geospatial layers & movement tracking (Milestone 2).")
    st.info("Regional OSINT/HUMINT and mobility layers will land in Milestone 2.")

elif page == "Social":
    ui.luxe_header("Social", "Community pulse via Reddit and trend signals (Milestone 2).")
    st.info("Reddit HUMINT and topic velocity will land in Milestone 2.")

elif page == "My Data":
    ui.luxe_header("My Data", "Bring your own sheets/logs for private overlays.")
    st.info("Uploads & overlays to be enabled after snapshots module (Milestone 3–4).")

elif page == "Methods":
    ui.luxe_header("Methods", "How metrics are computed.")
    ui.glossary_panel(show_full=True)
