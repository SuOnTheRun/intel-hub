# MUST COME FIRST
import streamlit as st
st.set_page_config(
    page_title="US — Intelligence Command Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

from theming import apply_white_lux_theme
apply_white_lux_theme()

# src/ui_us.py
from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone, date

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from .theming import set_dark_theme
from .collectors import (
    fetch_latest_news,
    fetch_tsa_throughput,
    fetch_market_snapshot,
)
from .risk_model import (
    compute_inputs,
    tension_breakdown,
    market_momentum,
)
from .narratives import strategist_playbook


# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def _fmt(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    if isinstance(x, float):
        return f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)


def _fmt_pct(x):
    try:
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
            return "—"
        return f"{x:.1f}%"
    except Exception:
        return "—"


def _relative(ts: pd.Timestamp) -> str:
    if not isinstance(ts, pd.Timestamp):
        return ""
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    delta = datetime.now(timezone.utc) - ts.to_pydatetime().astimezone(timezone.utc)
    s = int(delta.total_seconds())
    if s < 60:
        return f"{s}s ago"
    m = s // 60
    if m < 60:
        return f"{m}m ago"
    h = m // 60
    if h < 24:
        return f"{h}h ago"
    d = h // 24
    return f"{d}d ago"


def _section_title(label: str):
    st.markdown(f"<h3 class='section-title'>{label}</h3>", unsafe_allow_html=True)


def _subtitle_from_signals(tension, vix_val, tsa_val, sentiment_level: str | None):
    parts = []

    if isinstance(tension, float) and not np.isnan(tension):
        level = "calm" if tension < 40 else "balanced" if tension < 60 else "elevated"
        parts.append(f"Tension {tension:.1f} ({level})")

    if isinstance(vix_val, float) and not np.isnan(vix_val):
        band = "low" if vix_val < 15 else "mid" if vix_val < 22 else "high"
        parts.append(f"VIX {vix_val:.1f} ({band} stress)")

    if isinstance(tsa_val, float) and not np.isnan(tsa_val):
        sign = "above" if tsa_val >= 0 else "below"
        parts.append(f"Mobility {abs(tsa_val):.1f}% {sign} 2019")

    if sentiment_level:
        parts.append(f"Consumer mood {sentiment_level}")

    return " · ".join(parts) or "Live OSINT | HUMINT | Situational Awareness"


# -------------------------------------------------------------------------
# Consumer sentiment from headlines (social / narrative proxy)
# -------------------------------------------------------------------------

_sia: SentimentIntensityAnalyzer | None = None


def _ensure_sia() -> SentimentIntensityAnalyzer:
    global _sia
    if _sia is None:
        try:
            _sia = SentimentIntensityAnalyzer()
        except LookupError:
            nltk.download("vader_lexicon")
            _sia = SentimentIntensityAnalyzer()
    return _sia


def _consumer_sentiment_from_news(news_df: pd.DataFrame):
    """
    Build a 0–100 consumer sentiment index from recent US news headlines.

    - Uses NLTK VADER on title + summary text.
    - Aggregates to daily averages.
    - Returns:
        info: dict with current, delta_7d, label
        series_df: DataFrame with last 7 days for plotting
    """
    if news_df is None or news_df.empty:
        return None, pd.DataFrame()

    df = news_df.copy()
    if "time" not in df.columns:
        return None, pd.DataFrame()

    df["dt"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["dt"])
    if df.empty:
        return None, pd.DataFrame()

    df["date"] = df["dt"].dt.date
    text_cols = []
    for col in ["title", "summary", "description"]:
        if col in df.columns:
            text_cols.append(df[col].fillna(""))
    if not text_cols:
        text_cols = [df["title"].fillna("")]
    df["text"] = (" ".join(["{}"] * len(text_cols))).format(*text_cols) if len(text_cols) > 1 else text_cols[0]

    sia = _ensure_sia()
    df["compound"] = df["text"].map(lambda t: sia.polarity_scores(str(t))["compound"])

    # Map compound [-1,1] -> [0,100]
    df["index"] = (df["compound"] + 1.0) * 50.0

    daily = (
        df.groupby("date")["index"]
        .mean()
        .sort_index()
    )

    if daily.empty:
        return None, pd.DataFrame()

    # Last 7 calendar days including today (or most recent date in data)
    last_date: date = daily.index.max()
    window_start = last_date - pd.Timedelta(days=6)
    window = daily[(daily.index >= window_start) & (daily.index <= last_date)]

    if window.empty:
        return None, pd.DataFrame()

    current = float(window.iloc[-1])
    first = float(window.iloc[0])
    delta = current - first

    # Human label
    if current >= 65:
        level = "optimistic"
    elif current >= 50:
        level = "steady"
    elif current >= 40:
        level = "cautious"
    else:
        level = "stressed"

    info = {
        "current": current,
        "delta_7d": delta,
        "level": level,
    }

    series_df = window.to_frame(name="Consumer Sentiment Index")
    return info, series_df


# -------------------------------------------------------------------------
# Main render
# -------------------------------------------------------------------------

def render():
    set_dark_theme()

    # ----- Data pulls (guarded) ------------------------------------------
    try:
        inputs, frames = compute_inputs()
    except Exception:
        inputs = type(
            "Obj",
            (),
            dict(
                cisa_count_3d=0,
                fema_count_14d=0,
                gdelt_count=0,
                gdelt_tone_mean=0.0,
                vix_level=0.0,
                tsa_delta_pct=0.0,
            ),
        )()
        frames = {
            "gkg": pd.DataFrame(),
            "cisa": pd.DataFrame(),
            "fema": pd.DataFrame(),
            "tsa": pd.DataFrame(),
            "market_hist": pd.DataFrame(),
        }

    try:
        market_snap, market_hist = fetch_market_snapshot()
    except Exception:
        market_snap, market_hist = ({}, pd.DataFrame())

    try:
        news_df = fetch_latest_news(region="us", limit=120)
    except Exception:
        news_df = pd.DataFrame()

    tsa_df = frames.get("tsa", pd.DataFrame())
    cisa_df = frames.get("cisa", pd.DataFrame())
    fema_df = frames.get("fema", pd.DataFrame())

    # ----- Pre-compute sentiment & headlines -----------------------------
    sentiment_info, sentiment_series = _consumer_sentiment_from_news(news_df)

    headlines_md = ""
    if not news_df.empty and "title" in news_df.columns:
        newest = news_df.head(12).copy()
        lines = []
        for _, r in newest.iterrows():
            t = _relative(pd.to_datetime(r["time"]))
            src = str(r.get("source", "")).strip()
            title = str(r["title"]).replace("[", "(").replace("]", ")")
            url = r.get("link", "#")
            lines.append(f"- [{title}]({url}) — *{src} · {t}*")
        headlines_md = "\n".join(lines)

    # ----- Risk breakdown + headline metrics -----------------------------
    breakdown = tension_breakdown()
    tension = breakdown.get("index", float("nan")) if isinstance(breakdown, dict) else float("nan")
    vix_val = market_snap.get("VIX", float("nan"))
    tsa_val = tsa_df["delta_vs_2019_pct"].iloc[-1] if not tsa_df.empty else float("nan")

    # ----- Page header ---------------------------------------------------
    sentiment_level = sentiment_info["level"] if sentiment_info else None

    st.title("United States — Intelligence Command Center")
    st.caption(_subtitle_from_signals(tension, vix_val, tsa_val, sentiment_level))

    # ----- Top KPI strip -------------------------------------------------
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("National Tension Index", _fmt(tension))
        st.markdown(
            "<div class='calc-note'>Weighted composite of tone, volume, CISA, FEMA, VIX, TSA.</div>",
            unsafe_allow_html=True,
        )
    with col2:
        st.metric("VIX (Market Stress)", _fmt(vix_val))
        st.markdown(
            "<div class='calc-note'>Latest ^VIX close from free Yahoo Finance.</div>",
            unsafe_allow_html=True,
        )
    with col3:
        st.metric("Mobility Δ vs 2019", _fmt_pct(tsa_val))
        st.markdown(
            "<div class='calc-note'>TSA 7-day moving average vs 2019 baseline (same day-of-week).</div>",
            unsafe_allow_html=True,
        )

    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("CISA Alerts (3d)", _fmt(inputs.cisa_count_3d))
        st.markdown(
            "<div class='calc-note'>Count of CISA advisories in the last 72 hours.</div>",
            unsafe_allow_html=True,
        )
    with col5:
        st.metric("FEMA Declarations (14d)", _fmt(inputs.fema_count_14d))
        st.markdown(
            "<div class='calc-note'>Sum of daily FEMA disaster declarations in the last 14 days.</div>",
            unsafe_allow_html=True,
        )
    with col6:
        if sentiment_info:
            delta_symbol = "+" if sentiment_info["delta_7d"] >= 0 else ""
            label = sentiment_info["level"]
            st.metric(
                "Consumer Sentiment Index",
                _fmt(sentiment_info["current"]),
                f"{delta_symbol}{sentiment_info['delta_7d']:.1f} pts vs 7d",
            )
            st.markdown(
                "<div class='calc-note'>Headline-level sentiment (VADER) mapped to a 0–100 index.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.metric("Consumer Sentiment Index", "—")
            st.markdown(
                "<div class='calc-note'>Insufficient recent headlines to compute index.</div>",
                unsafe_allow_html=True,
            )

    st.write("")  # slim spacer

    # ----- Body layout: left = narrative, right = signals ----------------
    left, right = st.columns([1.8, 1.2])

    # LEFT – Situation brief, headlines, sentiment journey
    with left:
        # Situation brief
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        _section_title("Situation Brief")

        pts = []
        comp = breakdown.get("components", {}) if isinstance(breakdown, dict) else {}

        if comp:
            if comp.get("tone", {}).get("risk", 0) >= 60:
                pts.append("Narrative tone is **unfavourable** vs the last two weeks.")
            if comp.get("vix", {}).get("risk", 0) >= 60:
                pts.append("Market stress (**VIX**) is elevated vs its 1-year range.")
            if comp.get("tsa", {}).get("risk", 0) >= 60:
                pts.append("Mobility is **below** 2019 baseline momentum.")
        if inputs.cisa_count_3d > 0:
            pts.append(f"{inputs.cisa_count_3d} CISA advisories in the last 72 hours.")
        if inputs.fema_count_14d > 0:
            pts.append(f"{inputs.fema_count_14d} FEMA declarations in the last 14 days.")

        if sentiment_info:
            mood = sentiment_info["level"]
            delta = sentiment_info["delta_7d"]
            direction = "improved" if delta > 1 else "softened" if delta < -1 else "held broadly steady"
            pts.append(
                f"Headline-level consumer mood is **{mood}**, and has {direction} vs a week ago "
                f"({delta:+.1f} index points)."
            )

        if not pts:
            pts = ["No abnormal movements detected across core indicators in the last 24–72 hours."]

        for p in pts:
            st.markdown(f"- {p}")

        st.markdown("</div>", unsafe_allow_html=True)

        # Headlines
        if headlines_md:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            _section_title("Latest Headlines")
            st.markdown(headlines_md, unsafe_allow_html=True)
            st.markdown(
                "<div class='calc-note'>Feed: Google News (US edition). Times are approximate (UTC).</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # Sentiment journey
        if not sentiment_series.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Consumer Sentiment — 7-day Journey")
            st.line_chart(sentiment_series, height=180, use_container_width=True)
            st.markdown(
                "<div class='calc-note'>Daily average VADER sentiment of US news headlines, "
                "mapped to a 0–100 index.</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT – Macro pulse, mobility, CISA / FEMA tables
    with right:
        if not market_hist.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Macro Pulse")
            cols_to_plot = [c for c in ["S&P 500", "Nasdaq 100"] if c in market_hist.columns]
            if cols_to_plot:
                st.line_chart(market_hist[cols_to_plot].dropna(), height=160, use_container_width=True)
                mom = market_momentum(market_hist)
                sp = mom.get("S&P 500", 0.0)
                ndx = mom.get("Nasdaq 100", 0.0)
                st.markdown(
                    f"<div class='small'>20-day momentum — S&P 500: {sp:+.2f}% · Nasdaq 100: {ndx:+.2f}%</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

        if not tsa_df.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Mobility — TSA Throughput")
            chart_df = tsa_df[["current_7dma", "baseline_7dma"]].rename(
                columns={"current_7dma": "Current 7-dma", "baseline_7dma": "2019 7-dma"}
            )
            st.line_chart(chart_df, height=160, use_container_width=True)
            latest_delta = tsa_df["delta_vs_2019_pct"].iloc[-1]
            st.markdown(
                f"<div class='small'>Latest Δ vs 2019: {latest_delta:+.1f}% (7-day avg).</div>",
                unsafe_allow_html=True,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        if not cisa_df.empty:
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("CISA Advisories")
            # If title/summary columns exist, show them; otherwise keep counts.
            cols = ["time", "count"]
            for extra in ["title", "summary", "product_name"]:
                if extra in cisa_df.columns:
                    cols.append(extra)
            st.dataframe(
                cisa_df[cols],
                use_container_width=True,
                hide_index=True,
                column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")},
                height=180,
            )
            st.markdown("</div>", unsafe_allow_html=True)

        if not fema_df.empty:
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("FEMA Declarations")
            cols = ["time", "count"]
            for extra in ["state", "title", "declarationType", "incidentType"]:
                if extra in fema_df.columns:
                    cols.append(extra)
            st.dataframe(
                fema_df[cols],
                use_container_width=True,
                hide_index=True,
                column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")},
                height=180,
            )
            st.markdown("</div>", unsafe_allow_html=True)

    # ----- Strategist Playbook -------------------------------------------
    st.markdown("<h3 class='section-title'>Strategist Playbook</h3>", unsafe_allow_html=True)
    pb = strategist_playbook(breakdown, market_hist, tsa_df, news_df, sentiment_info)

    # Marketing posture
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Marketing posture**", unsafe_allow_html=True)
    if pb.get("marketing"):
        for b in pb["marketing"]:
            st.markdown(f"- {b}")
    else:
        st.markdown("- No major posture changes suggested by today’s signals.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Insight watchlist
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Insight watchlist**", unsafe_allow_html=True)
    for b in pb.get("insight", []):
        st.markdown(f"- {b}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Emerging topics
    topics = pb.get("topics", [])
    if topics:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Emerging topics (headlines)**", unsafe_allow_html=True)
        st.markdown("\n".join(topics), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption(
        "Sources: Google News (US), GDELT GKG v2, TSA Passenger Volumes, "
        "CISA Advisories, FEMA OpenFEMA, Yahoo Finance indices."
    )
