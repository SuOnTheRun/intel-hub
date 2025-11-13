# src/ui_us.py
from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from .theming import set_light_theme
from .collectors import fetch_latest_news, fetch_market_snapshot
from .risk_model import compute_inputs, tension_breakdown, market_momentum
from .narratives import strategist_playbook


# ---------- helpers ----------
def _fmt(x):
    if x is None or (isinstance(x, float) and np.isnan(x)): return "—"
    if isinstance(x, float): return f"{x:.2f}".rstrip("0").rstrip(".")
    return str(x)

def _fmt_pct(x):
    try:
        if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))): return "—"
        return f"{x:.1f}%"
    except Exception:
        return "—"

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

def _subtitle_from_signals(tension, vix_val, tsa_val):
    bits = []
    if isinstance(tension, (int, float)) and not np.isnan(tension):
        level = "calm" if tension < 40 else "balanced" if tension < 60 else "elevated"
        bits.append(f"Tension {tension:.1f} ({level})")
    if isinstance(vix_val, (int, float)) and not np.isnan(vix_val):
        band = "low" if vix_val < 15 else "mid" if vix_val < 22 else "high"
        bits.append(f"VIX {vix_val:.1f} ({band})")
    if isinstance(tsa_val, (int, float)) and not np.isnan(tsa_val):
        sign = "above" if tsa_val >= 0 else "below"
        bits.append(f"Mobility {abs(tsa_val):.1f}% {sign} 2019")
    return " · ".join(bits) or "Live OSINT | HUMINT | Situational Awareness"


# ---------- page ----------
def render():
    set_light_theme()
    st.title("United States — Intelligence Command Center")

    # Data pulls
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

    # headlines (US)
    try:
        news_df = fetch_latest_news(region="us", limit=50)
    except Exception:
        news_df = pd.DataFrame()

    headlines_md = ""
    if not news_df.empty:
        newest = news_df.head(14).copy()
        lines = []
        for _, r in newest.iterrows():
            t = _relative(pd.to_datetime(r["time"]))
            src = r.get("source","").strip()
            title = str(r["title"]).replace("[","(").replace("]",")")
            url = r["link"]
            lines.append(f"- [{title}]({url}) — *{src} · {t}*")
        headlines_md = "\n".join(lines)

    # metrics
    breakdown = tension_breakdown()
    tension = breakdown["index"]
    vix_val = market_snap.get("VIX", float("nan"))
    tsa_df = frames.get("tsa", pd.DataFrame())
    tsa_val = tsa_df["delta_vs_2019_pct"].dropna().iloc[-1] if not tsa_df.empty else float("nan")

    st.caption(_subtitle_from_signals(tension, vix_val, tsa_val))

    c1, c2, c3, c4, c5 = st.columns([1.2,1.2,1.2,1.2,1.2])
    with c1:
        st.metric("National Tension Index", _fmt(tension))
        st.caption("Weighted composite: tone, volume, CISA, FEMA, VIX, TSA.")
    with c2:
        st.metric("VIX (Market Stress)", _fmt(vix_val))
        st.caption("Latest ^VIX close (yfinance).")
    with c3:
        st.metric("Mobility Δ vs 2019", _fmt_pct(tsa_val))
        st.caption("TSA 7-day avg vs 2019 7-day avg.")
    with c4:
        st.metric("CISA Alerts (3d)", _fmt(inputs.cisa_count_3d))
        st.caption("Advisories in the past 72h.")
    with c5:
        st.metric("FEMA Declarations (14d)", _fmt(inputs.fema_count_14d))
        st.caption("Sum of daily declarations over 14d.")

    st.write("")

    left, right = st.columns([1.8, 1.25])

    # LEFT — Situation + Headlines + Per-state topics
    with left:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        _section_title("Situation Brief")
        pts = []
        comp = breakdown.get("components", {}) if isinstance(breakdown, dict) else {}
        if comp.get("tone", {}).get("risk", 0) >= 60:
            pts.append("News tone skews **negative** versus its 2-week history.")
        if comp.get("vix", {}).get("risk", 0) >= 60:
            pts.append("Market volatility is **elevated** relative to the 1-year range.")
        if comp.get("tsa", {}).get("risk", 0) >= 60:
            pts.append("Mobility momentum sits **below** the 2019 baseline.")
        if inputs.cisa_count_3d > 0:
            pts.append(f"{inputs.cisa_count_3d} CISA advisories in the last 72h.")
        if inputs.fema_count_14d > 0:
            pts.append(f"{inputs.fema_count_14d} FEMA declarations in the last 14d.")
        if isinstance(vix_val, float) and not np.isnan(vix_val):
            band = "low" if vix_val < 15 else "mid" if vix_val < 22 else "high"
            pts.append(f"VIX at **{vix_val:.1f}** ({band}).")
        if isinstance(tsa_val, float) and not np.isnan(tsa_val):
            sign = "above" if tsa_val >= 0 else "below"
            pts.append(f"Mobility vs 2019: **{tsa_val:+.1f}%** ({sign}).")
        if not pts:
            pts = ["Core indicators stable in the last 24–72 hours."]
        for p in pts: st.markdown(f"- {p}")
        st.markdown("</div>", unsafe_allow_html=True)

        if headlines_md:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            _section_title("Latest Headlines (US)")
            st.markdown(headlines_md, unsafe_allow_html=True)
            st.caption("Google News (US edition). Times approximate (UTC).")
            st.markdown("</div>", unsafe_allow_html=True)

        # Per-state topic snippets (from headlines text)
        from .narratives import strategist_playbook as _pb
        pb_preview = _pb(breakdown, market_hist, tsa_df, news_df)
        if pb_preview.get("topics_by_state"):
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            _section_title("Emerging Topics by State (headlines)")
            states = list(pb_preview["topics_by_state"].keys())[:12]
            for st_abbr in states:
                toks = " · ".join(pb_preview["topics_by_state"][st_abbr][:5])
                st.markdown(f"**{st_abbr}** — {toks}")
            st.markdown("</div>", unsafe_allow_html=True)

    # RIGHT — Macro/Mobility charts and detailed CISA/FEMA (show titles if present)
    with right:
        if not market_hist.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Market Pulse")
            st.line_chart(market_hist[["S&P 500","Nasdaq 100"]].dropna(), use_container_width=True, height=170)
            mom = market_momentum(market_hist)
            st.caption(f"20-day momentum — S&P 500: {mom.get('S&P 500',0):+.2f}% · Nasdaq 100: {mom.get('Nasdaq 100',0):+.2f}%")
            st.markdown("</div>", unsafe_allow_html=True)

        if not tsa_df.empty:
            st.markdown("<div class='chart-card'>", unsafe_allow_html=True)
            _section_title("Mobility")
            st.line_chart(tsa_df[["current_7dma","baseline_7dma"]].rename(columns={"current_7dma":"Current","baseline_7dma":"2019 Baseline"}),
                          height=170, use_container_width=True)
            st.caption(f"Latest Δ vs 2019: {tsa_val:+.1f}%")
            st.markdown("</div>", unsafe_allow_html=True)

        if not frames.get("cisa", pd.DataFrame()).empty:
            df = frames["cisa"].copy()
            cols = [c for c in ["time","title","summary","count"] if c in df.columns]
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("CISA Advisories")
            st.dataframe(df[cols].tail(8), use_container_width=True, hide_index=True,
                         column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")}, height=220)
            st.markdown("</div>", unsafe_allow_html=True)

        if not frames.get("fema", pd.DataFrame()).empty:
            df = frames["fema"].copy()
            cols = [c for c in ["time","title","summary","count","state"] if c in df.columns]
            st.markdown("<div class='card note-card'>", unsafe_allow_html=True)
            _section_title("FEMA Declarations")
            st.dataframe(df[cols].tail(8), use_container_width=True, hide_index=True,
                         column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD")}, height=220)
            st.markdown("</div>", unsafe_allow_html=True)

    # Strategist Playbook — uses real headlines & regimes
    st.markdown("<h3 class='section-title'>Strategist Playbook</h3>", unsafe_allow_html=True)
    pb = strategist_playbook(breakdown, market_hist, tsa_df, news_df)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Marketing posture**")
    if pb.get("marketing"):
        for b in pb["marketing"]: st.markdown(f"- {b}")
    else:
        st.markdown("- No posture changes suggested by today’s signals.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("**Insight watchlist**")
    for b in pb.get("insight", []): st.markdown(f"- {b}")
    st.markdown("</div>", unsafe_allow_html=True)

    if pb.get("topics"):
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("**Emerging topics (headlines)**")
        st.markdown("\n".join(pb["topics"]))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("Sources: Google News (US), GDELT GKG v2, TSA Passenger Volumes, CISA Advisories, FEMA OpenFEMA, yfinance.")
