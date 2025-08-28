import os
import streamlit as st
import pandas as pd

from src.theming import apply_page_style
from src.presets import region_names, region_bbox, region_center, region_keywords
from src.analytics import (
    enrich_news_with_topics_regions, aggregate_kpis, build_social_listening_panels,
    add_risk_scores, filter_by_controls, TOPIC_LIST, cluster_headlines,
    add_emotions, extend_kpis_with_intel,
)
from src.data_sources import (
    fetch_market_snapshot, fetch_rss_bundle, fetch_newsapi_bundle, merge_news_and_dedupe,
    fetch_google_trends, fetch_opensky_air_traffic, fetch_opensky_tracks_for_icao24,
    fetch_reddit_posts_if_configured, fetch_gdelt_events,
)
from src.maps import render_global_air_map, render_tracks_map
from src.ui import (
    render_header, render_markets, render_trends, render_reddit,
    render_regions_grid, render_feed_panel,
    render_kpi_row_intel, render_top_events_split,
    render_section_header, render_alert_strip, render_reliability_panel,
    # NEW: morning-briefing UI
    render_pulse_row, render_emotion_lens, render_topics_lens, render_psychology_console,
)
from src.exporters import download_buttons

# ========= MORNING BRIEFING METRICS & PSYCHOLOGY LEXICONS =========
import re
import pandas as pd
import numpy as np

def _pick_time_col(df):
    if df is None or df.empty:
        return None
    for c in ["published","published_at","date","datetime","timestamp","time","ts","created_utc","created","created_at"]:
        if c in df.columns:
            return c
    return None

def _coerce_time(df, col):
    s = df.copy()
    s[col] = pd.to_datetime(s[col], errors="coerce", utc=True)
    return s.dropna(subset=[col])

def _split_24h_windows(df, tcol):
    """Return two dataframes: last_24h, prev_24h (rolling back from the max timestamp)."""
    if df is None or df.empty or tcol is None:
        return pd.DataFrame(), pd.DataFrame()
    s = _coerce_time(df, tcol)
    if s.empty:
        return pd.DataFrame(), pd.DataFrame()
    end = s[tcol].max()
    start_last = end - pd.Timedelta(hours=24)
    start_prev = start_last - pd.Timedelta(hours=24)
    last = s[(s[tcol] > start_last) & (s[tcol] <= end)]
    prev = s[(s[tcol] > start_prev) & (s[tcol] <= start_last)]
    return last, prev

def global_risk_index_delta(df):
    """
    Mean risk (0–10) last 24h vs prior 24h.
    Returns dict: {'current': float, 'delta': float}
    """
    tcol = _pick_time_col(df)
    last, prev = _split_24h_windows(df, tcol)
    cur = float(last["risk_score"].mean()) if ("risk_score" in last.columns and not last.empty) else 0.0
    base = float(prev["risk_score"].mean()) if ("risk_score" in prev.columns and not prev.empty) else 0.0
    return {"current": round(cur, 2), "delta": round(cur - base, 2)}

def event_velocity_delta(df):
    """
    Events/hour in last 24h vs prior 24h.
    """
    tcol = _pick_time_col(df)
    last, prev = _split_24h_windows(df, tcol)
    def _vel(x):
        if x is None or x.empty:
            return 0.0
        x = x.copy()
        x["hour_bucket"] = pd.to_datetime(x[tcol], utc=True, errors="coerce").dt.floor("H")
        return float(x.groupby("hour_bucket").size().mean()) if not x.empty else 0.0
    cur = _vel(last)
    base = _vel(prev)
    return {"current": round(cur, 2), "delta": round(cur - base, 2)}

# --- Emotion / psychology indices (uses your existing emotion columns) ---
_NEG = ["emo_fear","emo_anger","emo_sadness"]
_POS = ["emo_joy","emo_trust"]

def psychological_state_index_delta(df):
    """
    Signed index = (neg - pos); last 24h vs prior 24h.
    Also returns the dominant emotion label in last 24h.
    """
    tcol = _pick_time_col(df)
    last, prev = _split_24h_windows(df, tcol)
    def _tilt(x):
        if x is None or x.empty:
            return 0.0
        for c in _NEG + _POS:
            if c not in x.columns:
                x[c] = 0.0
        neg = float(x[_NEG].mean().mean())
        pos = float(x[_POS].mean().mean())
        return float(neg - pos)
    cur = _tilt(last)
    base = _tilt(prev)
    dom = ""
    if "emo_dominant" in last.columns and not last.empty:
        try:
            dom = last["emo_dominant"].value_counts().idxmax()
        except Exception:
            dom = ""
    return {"current": round(cur, 3), "delta": round(cur - base, 3), "dominant": dom}

def engagement_friction_delta(reddit_df):
    """
    Friction = score / (comments+1). Higher => more passive; lower => more action.
    Returns last 24h vs prior 24h.
    """
    if reddit_df is None or getattr(reddit_df, "empty", True):
        return {"current": 0.0, "delta": 0.0}

    tcol = _pick_time_col(reddit_df)
    last, prev = _split_24h_windows(reddit_df, tcol)

    def _fric(x: pd.DataFrame) -> float:
        if x is None or x.empty:
            return 0.0
        s = x.copy()
        zero = pd.Series(0.0, index=s.index)
        score = pd.to_numeric(s["score"], errors="coerce") if "score" in s.columns else zero
        comments = pd.to_numeric(s["num_comments"], errors="coerce") if "num_comments" in s.columns else zero
        return float((score.fillna(0.0) / (comments.fillna(0.0) + 1.0)).mean())

    cur = _fric(last); base = _fric(prev)
    return {"current": round(cur, 3), "delta": round(cur - base, 3)}


# --- Psychology console (validation vs action vs next step) ---
_VAL_WORDS = set("""
why because justify belief identity reassure values loyalty safe stability confidence trust hope dignity
""".split())
_ACT_WORDS = set("""
how steps plan build deploy execute operate apply guide procedure instruction training strategy
""".split())
_NEXT_WORDS = set("""
next join register sign vote donate contact attend enlist apply buy subscribe commit adopt
""".split())
_RESIST_WORDS = set("""
can't cannot wont won't block ban delay refuse resist oppose sanction barrier shortage constraint cap
""".replace("’","'").split())

_token_re_psy = re.compile(r"[A-Za-z][A-Za-z\-']+")

def _count_psych_buckets(text):
    t = str(text or "").lower()
    counts = {"validation":0, "action":0, "next_step":0, "resistance":0}
    for tok in _token_re_psy.findall(t):
        if tok in _VAL_WORDS: counts["validation"] += 1
        if tok in _ACT_WORDS: counts["action"] += 1
        if tok in _NEXT_WORDS: counts["next_step"] += 1
        if tok in _RESIST_WORDS: counts["resistance"] += 1
    return counts

def psychology_buckets(df, text_col="title"):
    """
    Returns dict of mean rates per bucket using headlines.
    """
    if df is None or df.empty:
        return {"validation":0.0,"action":0.0,"next_step":0.0,"resistance":0.0}
    agg = {"validation":0, "action":0, "next_step":0, "resistance":0}
    n = 0
    for t in df[text_col].astype(str).fillna(""):
        c = _count_psych_buckets(t)
        for k in agg: agg[k] += c[k]
        n += 1
    if n == 0: n = 1
    return {k: round(v / n, 3) for k,v in agg.items()}



# ---------------- Page setup ----------------
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
    tickers = st.text_input(
        "Tickers (comma-separated)",
        value=os.getenv("DEFAULT_TICKERS","RELIANCE.NS,TCS.NS,INFY.NS,^NSEI,TSLA,AAPL,MSFT")
    )
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
social_panels = build_social_listening_panels(
    pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df,
    reddit_df
)

# ---------------- KPIs ----------------
kpis = aggregate_kpis(
    pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df,
    gdelt_df,
    air_df
)
kpis = extend_kpis_with_intel(kpis, news_df, gdelt_df if not gdelt_df.empty else None, air_df)

# Action bar — centered (no raw HTML)
_, center, _ = st.columns([1, 3, 1])
with center:
    download_buttons(
        news_df=news_df, gdelt_df=gdelt_df, markets_df=markets_df,
        air_df=air_df, trends_df=trends_df, reddit_df=reddit_df
    )


# Combined pool for overview analytics
event_pool = pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df

# Morning pulse (last 24h vs previous 24h)
pulse = {
    "risk":       global_risk_index_delta(event_pool),
    "velocity":   event_velocity_delta(event_pool),
    "psych":      psychological_state_index_delta(event_pool),
    "friction":   engagement_friction_delta(reddit_df),
}


# ---------------- Tabs (must be BEFORE the with-blocks) ----------------
tab_overview, tab_regions, tab_feed, tab_mobility, tab_markets, tab_social = st.tabs(
    ["Overview", "Regional Analysis", "Intelligence Feed", "Movement Tracking", "Markets", "Social Listening"]
)

# ---------------- Tab bodies ----------------
with tab_overview:
    # Alerts (simple examples; adjust thresholds if you like)
    alerts = []
    if kpis.get("mobility_anomalies", 0) > 500:
        alerts.append(f"Mobility anomalies elevated (≈{kpis['mobility_anomalies']})")
    if kpis.get("early_warning", 0) >= 6:
        alerts.append(f"Early Warning Index high ({kpis['early_warning']})")
    render_alert_strip(alerts)

     # Morning Pulse row (click cards to expand)
    render_pulse_row(pulse)

    # Strategic Highlights (formerly Scorecard)
    render_section_header(
        "Strategic Highlights",
        "* Early Warning Index blends risk (0–10), negative–positive emotion tilt, event velocity, and mobility anomalies; higher means more concerning."
    )
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)
    render_kpi_row_intel(kpis)
    st.markdown('</div>', unsafe_allow_html=True)

    # Top Events + HUMINT emotions
    top_events = pd.concat([clustered, clustered_gdelt], ignore_index=True) if not clustered_gdelt.empty else clustered
    render_top_events_split(top_events, n=20, title="Top Events")

    # Risk / Mobility Heat (GDELT if available, else air-traffic density)
    render_section_header(
        "Risk / Mobility Heat",
        "* Risk heat uses geocoded GDELT density when available; falls back to live air-traffic density for situational awareness."
    )

    # Emotion & Psychology Console
    render_emotion_lens(event_pool)
    render_topics_lens(event_pool)
    render_psychology_console(event_pool)

    from src.presets import region_center
    from src.maps import render_global_gdelt_map, render_global_air_map
    if not gdelt_df.empty and {"lat", "lon"}.issubset(set(gdelt_df.columns)):
        render_global_gdelt_map(gdelt_df, center=region_center(region), zoom=4)
    else:
        render_global_air_map(air_df, center=region_center(region), zoom=4)
    # Signal Reliability
    render_section_header(
        "Signal Reliability",
        "* Counts and last-update age for each feed (minutes since latest timestamp)."
    )

    def _last_ts_age(df):
        if df is None or getattr(df, "empty", True):
            return None, None
        tcol = next((c for c in ["published","published_at","date","datetime","timestamp","time","ts","created_utc","created","created_at"] if c in df.columns), None)
        if not tcol:
            return None, None
        s = pd.to_datetime(df[tcol], errors="coerce", utc=True).dropna()
        if s.empty:
            return None, None
        last = s.max()
        age = (pd.Timestamp.utcnow() - last).total_seconds() / 60.0
        return last, round(age, 1)

    f_news   = _last_ts_age(news_df)
    f_gdelt  = _last_ts_age(gdelt_df)
    f_reddit = _last_ts_age(reddit_df)

    freshness = {
        "news":   {"count": len(news_df)   if news_df   is not None else 0, "last_ts": f_news[0],   "age_min": f_news[1]},
        "gdelt":  {"count": len(gdelt_df)  if gdelt_df  is not None else 0, "last_ts": f_gdelt[0],  "age_min": f_gdelt[1]},
        "air":    {"count": len(air_df)    if air_df    is not None else 0, "last_ts": None,        "age_min": None},
        "trends": {"count": len(trends_df) if trends_df is not None else 0, "last_ts": None,        "age_min": None},
        "reddit": {"count": len(reddit_df) if reddit_df is not None else 0, "last_ts": f_reddit[0], "age_min": f_reddit[1]},
    }

    src_counts = {
        "news": len(news_df) if news_df is not None else 0,
        "gdelt": len(gdelt_df) if gdelt_df is not None else 0,
        "air": len(air_df) if air_df is not None else 0,
        "trends": len(trends_df) if trends_df is not None else 0,
        "reddit": len(reddit_df) if reddit_df is not None else 0,
    }

    render_reliability_panel(freshness, src_counts, col_label="Feed")


with tab_regions:
    render_regions_grid(
        pd.concat([news_df, gdelt_df], ignore_index=True) if not gdelt_df.empty else news_df,
        expanded=True
    )

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

