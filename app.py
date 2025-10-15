# app.py — Intelligence Hub (robust loader + Executive Summary)

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
    st.error("Startup import failed. Details below (shown here to avoid a 502).")
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
    df = emotions.add_sentiment(df)  # lightweight build uses lexicon-based tone
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
    except Exception:
        news_df = pd.DataFrame(columns=["category","title","link","published","summary","source","published_dt","sentiment"])

    try:
        base = load_category_metrics()
    except Exception:
        base = pd.DataFrame(columns=["category","trends","market_pct"])

    try:
        heat = analytics.build_category_heatmap(news_df, base)
    except Exception:
        heat = pd.DataFrame(columns=["category","news_z","sentiment","market_pct","composite","news_count","trends"])

# ======================================================================
# Routes
# ======================================================================
if page == "Command Center":
    ui.luxe_header(
        title="Command Center",
        subtitle="A live read on category momentum, tone, markets, and public interest — distilled for action."
    )

    # HUMINT layers (silent fallbacks)
    with st.spinner("Computing HUMINT layers…"):
        try:
            ent_df = entities.extract_entities(news_df, top_n=8)
        except Exception:
            ent_df = pd.DataFrame(columns=["category","label","entity","count"])
        try:
            tension_df = riskmodel.compute_tension(news_df, heat, ent_df)
        except Exception:
            tension_df = pd.DataFrame(columns=["category","tension_0_100","neg_density","sent_vol","news_z","market_drawdown","trends_norm","entity_intensity"])

    # KPI ribbon + Highlights
    ui.kpi_ribbon(heat_df=heat, tension_df=tension_df, news_df=news_df)
    ui.highlights_panel(heat, tension_df)

    # Executive Summary (new)
    st.markdown("---")
    st.header("Executive Summary")
    ui.insights_summary(heat_df=heat, news_df=news_df, tension_df=tension_df, max_items=8)

    # Heatmap
    st.subheader("Category Heatmap (24–72h)")
    ui.heatmap_labeled(heat)
    st.caption("Interpretation: red = unusually busy news flow; blue = quieter. Tone > 0 is supportive; market % > 0 is up. Hover for values. Drag to zoom; double-click to reset.")

    # Sentiment explainer
    ui.sentiment_explainer(heat, news_df)

    st.markdown("---")
    st.header("HUMINT Deep-Dive")

    # Narratives
    with st.spinner("Deriving narratives…"):
        try:
            narr = narratives.build_narratives(news_df, top_n=3)
        except Exception:
            from types import SimpleNamespace
            narr = SimpleNamespace(table=pd.DataFrame(columns=["category","narrative","weight","n_docs"]), top_docs_by_cat={})
    ui.narratives_panel(narr.table, narr.top_docs_by_cat)

    # Entities
    st.subheader("Prominent Entities (ORG / PERSON / GPE)")
    if 'ent_df' in locals() and not ent_df.empty:
        st.dataframe(ent_df, use_container_width=True)
    else:
        st.caption("No entities extracted.")

    # Tension table
    ui.tension_panel(tension_df)

    # Headlines
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
