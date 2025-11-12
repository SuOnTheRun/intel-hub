# src/ui_us.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from .theming import set_dark_theme
from .collectors import (
    fetch_latest_news, fetch_tsa_throughput, fetch_market_snapshot,
)
from .risk_model import compute_inputs, compute_tension_index, tension_breakdown, market_momentum
from .narratives import strategist_playbook
from .narratives import strategist_playbook

def _fmt(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    if isinstance(x, float): 
        return f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)

def _relative(ts: pd.Timestamp) -> str:
    if not isinstance(ts, pd.Timestamp): return ""
    if ts.tzinfo is None: ts = ts.tz_localize("UTC")
    delta = datetime.now(timezone.utc) - ts.to_pydatetime().astimezone(timezone.utc)
    s = int(delta.total_seconds())
    if s < 60: return f"{s}s ago"
    m = s//60
    if m < 60: return f"{m}m ago"
    h = m//60
    if h < 24: return f"{h}h ago"
    d = h//24
    return f"{d}d ago"

def _section_title(label): 
    st.markdown(f"<h3 class='section-title'>{label}</h3>", unsafe_allow_html=True)

def render():
    set_dark_theme()
    st.title("United States — Intelligence Command Center")
    st.caption("Live OSINT | HUMINT | Situational Awareness & Early Warning")

    # -------- Data pulls (guarded) --------
    try:
        inputs, frames = compute_inputs()
    except Exception:
        inputs = type("Obj", (), dict(
            cisa_count_3d=0, fema_count_14d=0, gdelt_count=0,
            gdelt_tone_mean=0.0, vix_level=0.0, tsa_delta_pct=0.0
        ))()
        frames = {"gkg": pd.DataFrame(), "cisa": pd.DataFrame(), "fema": pd.DataFrame(),
                  "tsa": pd.DataFrame(), "market_hist": pd.DataFrame()}
    try:
        market_snap, market_hist = fetch_market_snapshot()
    except Exception:
        market_snap, market_hist = ({}, pd.DataFrame())
    tsa_df = frames.get("tsa", pd.DataFrame())
    news_df = pd.DataFrame()
    try:
        news_df = fetch_latest_news(region="us", limit=40)
    except Exception:
        news_df = pd.DataFrame()

    # Compute headline list early
    headlines = []
    if not news_df.empty:
        newest = news_df.head(12).copy()
        for _, r in newest.iterrows():
            t = _relative(pd.to_datetime(r["time"]))
            src = r.get("source","")
            headlines.append(f"• [{r['title']}]({r['link']})  <span class='small'>— {src} · {t}</span>")
    
    # -------- Top metrics (sparse, minimal) --------
    breakdown = tension_breakdown()
    tension = breakdown["index"]
    vix_val = market_snap.get("VIX", float("nan"))
    tsa_val = tsa_df["delta_vs_2019_pct"].iloc[-1] if not tsa_df.empty else np.nan

    m1, m2, m3, m4, m5 = st.columns([1.2,1.2,1.2,1.2,1.2])
    with m1:
        st.metric("National Tension Index", f"{_fmt(tension)}")
        st.markdown("<div class='calc-note'>Percentile-weighted composite of tone, volume, CISA, FEMA, VIX, TSA.</div>", unsafe_allow_html=True)
    with m2:
        st.metric("VIX (Market Stress)", f"{_fmt(vix_val)}")
        st.markdown("<div class='calc-note'>Latest ^VIX close (yfinance history).</div>", unsafe_allow_html=True)
    with m3:
        st.metric("Mobility Δ vs 2019", f"{_fmt(tsa_val)}%")
        st.markdown("<div class='calc-note'>TSA 7-day avg vs 2019 7-day avg.</div>", unsafe_allow_html=True)
    with m4:
        st.metric("CISA Alerts (3d)", f"{_fmt(inputs.cisa_count_3d)}")
        st.markdown("<div class='calc-note'>Count of advisories past 72h.</div>", unsafe_allow_html=True)
    with m5:
        st.metric("FEMA Declarations (14d)", f"{_fmt(inputs.fema_count_14d)}")
        st.markdown("<div class='calc-note'>Sum of daily declarations over 14d.</div>", unsafe_allow_html=True)

    st.write("")  # thin spacer

    # -------- Body: 2 columns, left = intelligence, right = signals --------
    left, right = st.columns([1.9, 1.2])

    # LEFT — Situation + Headlines (no huge boxes, just clean cards)
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        _section_title("Situation Report")
        # Build 3–6 concise points from available signals (no placeholders)
        pts = []
        comp = breakdown["components"]
        if comp:
            if comp["tone"]["risk"] >= 60: pts.append("Narrative tone is **unfavourable** vs its 2-week history.")
            if comp["vix"]["risk"] >= 60: pts.append("Market stress (**VIX**) is elevated versus its 1-year range.")
            if comp["tsa"]["risk"] >= 60: pts.append("Mobility is **below** 2019 baseline momentum.")
            if inputs.cisa_count_3d > 0:  pts.append(f"{inputs.cisa_count_3d} CISA advisories in the past 72h.")
            if inputs.fema_count_14d > 0: pts.append(f"{inputs.fema_count_14d} FEMA declarations in the past 14d.")
        if not pts: pts = ["No abnormal signals detected across core indicators in the last 24–72 hours."]
        for p in pts: st.markdown(f"- {p}")
        st.markdown("</div>", unsafe_allow_html=True)

        if headlines:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            _section_title("Latest Headlines")
            st.markdown("\n".join(headlines), unsafe_allow_html=True)
            st.markdown("<div class='calc-note'>Feed: Google News (US edition). Times are approximate (UTC).</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT — Macro & Activity signals (only show if we actually have data)
    with right:
        if not market_hist.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Macro Pulse")
            st.line_chart(market_hist[["S&P 500","Nasdaq 100"]].dropna(), use_container_width=True, height=160)
            mom = market_momentum(market_hist)
            st.markdown(f"<div class='small'>20-day momentum — S&P 500: {mom.get('S&P 500',0):+.2f}% · Nasdaq 100: {mom.get('Nasdaq 100',0):+.2f}%</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if not tsa_df.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Mobility")
            st.line_chart(tsa_df[["current_7dma","baseline_7dma"]].rename(columns={"current_7dma":"Current","baseline_7dma":"2019 Baseline"}), height=160, use_container_width=True)
            st.markdown(f"<div class='small'>Latest Δ vs 2019: {tsa_df['delta_vs_2019_pct'].iloc[-1]:+.1f}%</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # Small vertical list: recent government items (when available)
        if not frames.get("cisa", pd.DataFrame()).empty:
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("CISA Advisories")
            st.dataframe(frames["cisa"][["time","count"]], use_container_width=True, hide_index=True,
                         column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")}, height=140)
            st.markdown("</div>", unsafe_allow_html=True)

        if not frames.get("fema", pd.DataFrame()).empty:
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("FEMA Declarations")
            st.dataframe(frames["fema"][["time","count"]], use_container_width=True, hide_index=True,
                         column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")}, height=140)
            st.markdown("</div>", unsafe_allow_html=True)
    # --- Strategist Playbook (clean header, two compact cards) ---
    st.markdown("<h3 class='section-title'>Strategist Playbook</h3>", unsafe_allow_html=True)

    pb = strategist_playbook(breakdown, market_hist, tsa_df, news_df)

    # Marketing posture
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Marketing posture**", unsafe_allow_html=True)
    if pb["marketing"]:
        for b in pb["marketing"]:
            st.markdown(f"- {b}")
    else:
        st.markdown("- No posture changes suggested by today’s signals.")
    st.markdown("</div>", unsafe_allow_html=True)

    # Insight watchlist
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Insight watchlist**", unsafe_allow_html=True)
    for b in pb["insight"]:
        st.markdown(f"- {b}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Emerging topics (from real headlines)
    if pb["topics"]:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Emerging topics (headlines)**", unsafe_allow_html=True)
        st.markdown("\n".join(pb["topics"]), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("Sources: Google News (RSS), GDELT GKG v2, TSA Passenger Volumes, CISA Advisories, FEMA OpenFEMA, yfinance indices.")
