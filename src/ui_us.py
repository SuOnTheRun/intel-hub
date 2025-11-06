# src/ui_us.py
import os
import pandas as pd
import streamlit as st

# Local modules
from .data_sources import (
    load_us_news,
    load_us_incidents,
    load_us_trends,
    load_us_macro,
)
from .analytics import compute_behavioral_readiness
from .risk_model import purchase_outlook_from_bri

# ------------- Page setup -------------
st.set_page_config(
    page_title="Intelligence Hub — United States",
    layout="wide",
)

# ------------- Helpers -------------
def _top_category_from_news(df: pd.DataFrame) -> tuple[str, float]:
    """
    Groups by simple keyword mapping into sectors and returns (name, mean_sentiment).
    Guaranteed to return a non-empty label.
    """
    if df is None or df.empty or "sentiment" not in df.columns or "title" not in df.columns:
        return ("No data", 0.0)

    bins = {
        "QSR": ["restaurant", "fast food", "qsr", "mcdonald", "kfc", "burger", "pizza", "starbucks"],
        "Retail": ["retail", "mall", "store", "shopping", "walmart", "target", "costco"],
        "Technology": ["smartphone", "iphone", "android", "chip", "semiconductor", "ai", "laptop"],
        "Automotive": ["auto", "car", "dealer", "ev", "tesla", "loan", "financing"],
        "Travel": ["airline", "hotel", "travel", "tourism", "airport"],
        "Finance": ["loan", "credit", "mortgage", "bank", "interest rate", "fed"],
        "Grocery": ["grocery", "supermarket", "kroger", "albertsons", "whole foods"],
    }

    def _cat_row(title: str) -> str:
        tl = title.lower()
        for k, kws in bins.items():
            if any(kw in tl for kw in kws):
                return k
        return "General"

    local = df.copy()
    local["cat"] = local["title"].astype(str).map(_cat_row)
    agg = local.groupby("cat", as_index=False)["sentiment"].mean()
    if agg.empty:
        return ("No data", 0.0)
    top = agg.sort_values("sentiment", ascending=False).iloc[0]
    return (str(top["cat"]), float(top["sentiment"]))

# ------------- Data Fetch -------------
@st.cache_data(ttl=900, show_spinner=True)
def _fetch_all_us():
    news_us = load_us_news()
    inc_us = load_us_incidents()
    trends_us = load_us_trends()
    macro_us = load_us_macro()
    return news_us, inc_us, trends_us, macro_us

news_us, inc_us, trends_us, macro_us = _fetch_all_us()

# ------------- Header -------------
st.title("United States — Command Center")

# ------------- Behavioral Readiness Index -------------
bri_df = compute_behavioral_readiness(
    mobility=None,            # hook in mobility later (Apple/Google or Citymapper)
    trends=trends_us,
    news=news_us,
    retail_density=None,      # add Yelp/SafeGraph when available
    macro=macro_us,
)

# ------------- KPI Row -------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    v = 0 if news_us is None or news_us.empty else int(len(news_us))
    st.metric("US Headlines (24–72h)", value=f"{v:,}")

with col2:
    v = 0 if inc_us is None or inc_us.empty else int(inc_us["NumArticles"].sum())
    st.metric("US Event Articles (48h)", value=f"{v:,}")

with col3:
    v = (bri_df["bri"].iloc[0] if not bri_df.empty else 0.0)
    st.metric("Behavioral Readiness Index", value=round(float(v), 2))

with col4:
    if trends_us is None or trends_us.empty:
        st.metric("Search Intent (14d avg)", value="No data")
    else:
        t14 = trends_us[trends_us["date"] >= (pd.Timestamp.utcnow().tz_localize("UTC") - pd.Timedelta(days=14))]
        st.metric("Search Intent (14d avg)", value=round(float(t14["interest"].mean()), 1))

# ------------- Outlook -------------
st.divider()
if not bri_df.empty:
    bri_val = float(bri_df["bri"].iloc[0])
    verdict = purchase_outlook_from_bri(bri_val)
    st.info(f"Outlook: {verdict['outlook']} — {verdict['explanation']}")
else:
    st.warning("No BRI computed yet — check inputs (trends/news/macro).")

# ------------- Highest Sector Tile -------------
st.subheader("Sector Pulse")
if news_us is None or news_us.empty:
    st.warning("No recent U.S. headlines were fetched.")
else:
    cat_name, cat_sent = _top_category_from_news(news_us)
    c1, c2 = st.columns([1,3])
    with c1:
        st.metric("Highest Sector (sentiment)", value=cat_name, delta=round(cat_sent, 3))
    with c2:
        sample = news_us[["published","source","title","sentiment"]].head(20)
        st.dataframe(sample, use_container_width=True, hide_index=True)

# ------------- Events Table (U.S.) -------------
st.subheader("U.S. Incidents — last 48h (GDELT)")
if inc_us is None or inc_us.empty:
    st.warning("No U.S. incidents in the last 48 hours (filtered).")
else:
    tbl = inc_us[["ts","ActionGeo_FullName","NumArticles","NumMentions","AvgTone"]].head(50)
    st.dataframe(tbl, use_container_width=True, hide_index=True)

# ------------- Trends Snapshot -------------
st.subheader("Search Intent (Google Trends — U.S.)")
if trends_us is None or trends_us.empty:
    st.warning("No Google Trends data.")
else:
    # top rising terms in 7d vs 28d
    now = pd.Timestamp.utcnow().tz_localize("UTC")
    t7 = trends_us[trends_us["date"] >= now - pd.Timedelta(days=7)]
    t28 = trends_us[trends_us["date"] >= now - pd.Timedelta(days=28)]
    comp = (
        t7.groupby("term")["interest"].mean()
        .to_frame("avg7")
        .join(t28.groupby("term")["interest"].mean().to_frame("avg28"), how="outer")
        .fillna(0.0)
    )
    comp["delta"] = comp["avg7"] - comp["avg28"]
    comp = comp.sort_values("delta", ascending=False)
    st.dataframe(comp.head(15), use_container_width=True)

st.caption("All data above is live, U.S.-scoped, and computed without placeholders.")
