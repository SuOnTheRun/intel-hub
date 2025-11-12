# src/ui_us.py
from __future__ import annotations
import streamlit as st
import pandas as pd

from .theming import set_dark_theme, hlabel
from .collectors import (
    fetch_latest_news, fetch_tsa_throughput, fetch_market_snapshot,
    fetch_cisa_alerts, fetch_fema_disasters, fetch_gdelt_gkg_last_n_days
)
from .analytics import sentiment_score, drift
from .risk_model import compute_inputs, compute_tension_index, market_momentum
from .narratives import strategic_brief
def render():
    set_dark_theme()
    st.title("United States — Intelligence Command Center")
    st.caption("Live OSINT | HUMINT | Situational Awareness & Early Warning")
    st.write("")  # subtle spacer under the title

    # === DATA PULLS (shielded) ===
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
    news_df = fetch_latest_news(region="us", limit=40)
    cisa_df = frames.get("cisa", pd.DataFrame())
    fema_df = frames.get("fema", pd.DataFrame())

    # === DATA PULLS (shielded) ===
    try:
        inputs, frames = compute_inputs()
    except Exception:
        # If any upstream source blows up, keep the page alive with empty frames.
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
    tsa_df   = frames.get("tsa", pd.DataFrame())
    news_df  = fetch_latest_news(region="us", limit=40)
    cisa_df  = frames.get("cisa", pd.DataFrame())
    fema_df  = frames.get("fema", pd.DataFrame())


    # === METRIC DECK ===
    from .methodology import method_note
    from .risk_model import tension_breakdown

    breakdown = tension_breakdown()
    tension = breakdown["index"]

    colA, colB, colC, colD, colE = st.columns([1.2,1.2,1.2,1.2,1.2])
    colA.metric("National Tension Index", f"{tension}")
    with colA.expander("How this is calculated"):
        st.markdown(method_note("tension_index"))
        # also show the live component audit:
        comp = breakdown["components"]
        st.markdown(
            f"- **Components (latest · percentile · contribution · weight)**  \n"
            f"  - Tone: `{comp['tone']['latest']:+.3f}` · `{comp['tone']['percentile']:.2f}` · `{comp['tone']['risk']:.1f}` · `{comp['tone']['weight']:.2f}`  \n"
            f"  - Volume: `{comp['volume']['latest']:.0f}` · `{comp['volume']['percentile']:.2f}` · `{comp['volume']['risk']:.1f}` · `{comp['volume']['weight']:.2f}`  \n"
            f"  - CISA: `{comp['cisa']['latest']:.0f}` · `{comp['cisa']['percentile']:.2f}` · `{comp['cisa']['risk']:.1f}` · `{comp['cisa']['weight']:.2f}`  \n"
            f"  - FEMA: `{comp['fema']['latest']:.0f}` · `{comp['fema']['percentile']:.2f}` · `{comp['fema']['risk']:.1f}` · `{comp['fema']['weight']:.2f}`  \n"
            f"  - VIX: `{comp['vix']['latest']:.2f}` · `{comp['vix']['percentile']:.2f}` · `{comp['vix']['risk']:.1f}` · `{comp['vix']['weight']:.2f}`  \n"
            f"  - TSA Δ%: `{comp['tsa']['latest']:+.2f}` · `{comp['tsa']['percentile']:.2f}` · `{comp['tsa']['risk']:.1f}` · `{comp['tsa']['weight']:.2f}`"
        )

    colB.metric("VIX (Market Stress)", f"{market_snap.get('VIX','—')}")
    with colB.expander("How this is calculated"):
        st.markdown(method_note("vix_level"))

    if not tsa_df.empty:
        colC.metric("Mobility Δ vs 2019", f"{tsa_df['delta_vs_2019_pct'].iloc[-1]:.1f}%")
    else:
        colC.metric("Mobility Δ vs 2019", "—")
    with colC.expander("How this is calculated"):
        st.markdown(method_note("tsa_delta"))

    colD.metric("CISA Alerts (3d)", f"{inputs.cisa_count_3d}")
    with colD.expander("How this is calculated"):
        st.markdown(method_note("cisa_3d"))

    colE.metric("FEMA Declarations (14d)", f"{inputs.fema_count_14d}")
    with colE.expander("How this is calculated"):
        st.markdown(method_note("fema_14d"))

    # === LAYOUT: 3 COLUMNS ===
    left, mid, right = st.columns([1.8, 1.6, 1.2])

    # LEFT: Headlines + CISA
    with left:
        hlabel("Latest Headlines", badge="OSINT")
        if news_df.empty:
            st.info("No headlines at the moment.")
        else:
            st.dataframe(
                news_df[["time","source","title"]],
                use_container_width=True, hide_index=True,
                column_config={"time": st.column_config.DatetimeColumn(format="YYYY-MM-DD HH:mm")}
            )

        hlabel("CISA Advisories", badge="Cyber", badge_class="risk")
        if cisa_df.empty:
            st.info("No recent CISA advisories.")
        else:
            st.dataframe(cisa_df[["time","title"]], use_container_width=True, hide_index=True)

    # MIDDLE: Markets, Mobility, GDELT Tone
    with mid:
            hlabel("Macro Pulse", badge="Markets")
    if not market_hist.empty:
        st.line_chart(market_hist[["S&P 500","Nasdaq 100"]].dropna(), use_container_width=True, height=180)
        mom = market_momentum(market_hist)
        st.caption(f"20-day momentum — S&P 500: {mom.get('S&P 500',0):+.2f}% | Nasdaq 100: {mom.get('Nasdaq 100',0):+.2f}%")

        # ▼ ADD THIS EXPANDER RIGHT HERE ▼
        with st.expander("How this is calculated — Momentum"):
            from .methodology import method_note
            st.markdown(method_note("market_momentum"))
        # ▲ END INSERT ▲

    else:
        st.info("Awaiting market history.")


        hlabel("Mobility — TSA Throughput (7-day avg)", badge="Activity")
        if not tsa_df.empty:
            st.line_chart(tsa_df[["current_7dma","baseline_7dma"]].rename(columns={"current_7dma":"Current","baseline_7dma":"2019 Baseline"}), height=180, use_container_width=True)
            st.caption(f"Latest delta vs 2019: {tsa_df['delta_vs_2019_pct'].iloc[-1]:+.1f}%  |  7-day drift: {drift(tsa_df['current_7dma']):+.2f}%")
        else:
            st.info("TSA data unavailable right now.")

            hlabel("News Tone (GDELT GKG)", badge="Narratives")
    gkg = frames["gkg"]
    if not gkg.empty:
        tone_series = gkg.set_index("datetime")["tone"].resample("3H").mean().dropna().tail(120)
        if not tone_series.empty:
            st.line_chart(tone_series, use_container_width=True, height=160)
            st.caption(f"Mean tone (last 48h): {tone_series.mean():+.2f}")

            # ▼ ADD THIS EXPANDER RIGHT HERE ▼
            with st.expander("How this is calculated — GDELT Tone"):
                from .methodology import method_note
                st.markdown(method_note("gdelt_tone"))
            # ▲ END INSERT ▲

        else:
            st.info("Insufficient points for tone trend.")
    else:
        st.info("GDELT feed empty at the moment.")


    # RIGHT: Strategic Brief + FEMA
    with right:
        hlabel("Strategic Brief", badge="HUMINT")
        brief = strategic_brief(tension, news_df)
        st.markdown(brief["summary"])
        st.markdown("**Next Moves / Watchlist**")
        for p in brief["next_steps"]:
            st.markdown(f"- {p}")

        hlabel("FEMA Declarations", badge="Gov")
        if fema_df.empty:
            st.info("No recent FEMA declarations in the last 14 days.")
        else:
            st.dataframe(fema_df[["time","state","type","title"]], use_container_width=True, hide_index=True)

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("Sources: Google News (RSS), GDELT GKG v2, TSA Passenger Volumes, CISA Advisories, FEMA OpenFEMA, yfinance indices.")
