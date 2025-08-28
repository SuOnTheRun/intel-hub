import streamlit as st
import pandas as pd
import plotly.express as px

import plotly.graph_objects as go
import streamlit as st
from html import escape
import numpy as np



def render_alert_strip(alerts: list[str]):
    if not alerts:
        return
    safe = " • ".join(escape(a) for a in alerts)
    st.markdown(
        """
        <div style="
            background:#0E1117;
            border:1px solid #2A2F3A;
            padding:10px 14px;
            border-radius:12px;
            font-size:14px;">
        <b>Alerts</b> — """ + safe + "</div>",
        unsafe_allow_html=True,
    )



def render_reliability_panel(freshness: dict, counts: dict, col_label="Feed"):
    """
    Small table: source freshness + counts so the overview feels reliable.
    """
    if not freshness:
        return
    rows = []
    for name, meta in freshness.items():
        rows.append({
            col_label: name,
            "Items": meta.get("count"),
            "Last Update (UTC)": str(meta.get("last_ts")) if meta.get("last_ts") is not None else "—",
            "Age (min)": meta.get("age_min") if meta.get("age_min") is not None else "—",
        })
    df = pd.DataFrame(rows)
    st.markdown("##### Signal Reliability")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if counts:
        st.caption("Top sources (by item count): " + ", ".join(f"{k} ({v})" for k, v in list(counts.items())[:8]))

def render_event_cards_with_emotion(df, title, n=12):
    """
    Enhanced event cards: headline, meta (region/topic/risk/age/source), micro emotion bars, link.
    """
    if df is None or df.empty:
        st.write("No events in window.")
        return
    st.subheader(title)
    show = df.head(n).copy()

    # Derive 'age' if we can
    time_col = None
    for c in ["published", "published_at", "date", "datetime", "timestamp", "time", "ts"]:
        if c in show.columns:
            time_col = c
            break
    if time_col is not None:
        show["_dt"] = pd.to_datetime(show[time_col], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        show["_age_min"] = (now - show["_dt"]).dt.total_seconds() / 60.0
    else:
        show["_age_min"] = np.nan

    cols = st.columns(3)
    for i, (_, row) in enumerate(show.iterrows()):
        with cols[i % 3]:
            st.markdown(f"**{row.get('title','')}**")

            # meta line
            region = row.get("region", "Global")
            topic = row.get("topic", "General")
            risk  = row.get("risk_score", "—")
            src   = row.get("source", row.get("provider", row.get("site", row.get("domain", "—"))))
            age_s = f"{int(row['_age_min'])}m ago" if pd.notna(row.get("_age_min")) else "—"
            st.caption(f"{region} · {topic} · Risk {risk} · {age_s} · {src}")

            # emotion microbar
            emo = [row.get(f"emo_{k}",0.0) for k in ["fear","anger","sadness","joy","trust"]]
            efig = go.Figure(go.Bar(x=["Fear","Anger","Sadness","Joy","Trust"], y=emo))
            efig.update_layout(height=120, margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
            st.plotly_chart(efig, use_container_width=True, config={"displayModeBar": False})

            url = row.get("url")
            if isinstance(url, str) and url:
                st.link_button("Open source", url)


def render_kpi_row_intel(kpis):
    # Row 1: your current KPIs
    cols1 = st.columns(5)
    cols1[0].metric("Intelligence Reports", kpis.get("intelligence_reports", "—"))
    cols1[1].metric("Movement Detections", kpis.get("movement_detections", "—"))
    cols1[2].metric("High-Risk Regions", kpis.get("high_risk_regions", "—"))
    cols1[3].metric("Aircraft Tracked", kpis.get("aircraft_tracked", "—"))
    cols1[4].metric("Avg Risk Score", kpis.get("avg_risk_score", "—"))

    # Row 2: new intelligence KPIs
    cols2 = st.columns(4)
    cols2[0].metric("Early Warning Index", kpis.get("early_warning", 0.0))
    cols2[1].metric("Event Velocity (per hr)", kpis.get("event_velocity", 0.0))
    cols2[2].metric("Mobility Anomalies", kpis.get("mobility_anomalies", 0))
    cols2[3].metric("Dominant Emotion", kpis.get("emo_dominant_top", "—"))

    # Emotion mix mini-bar
    labels = ["Anger","Antic.","Disgust","Fear","Joy","Sadness","Surprise","Trust"]
    mix = [kpis.get(f"emo_{k.lower()}", 0.0) for k in ["Anger","Anticipation","Disgust","Fear","Joy","Sadness","Surprise","Trust"]]
    fig = go.Figure(go.Bar(x=labels, y=mix))
    fig.update_layout(height=180, margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_section_header(title: str, note: str | None = None):
    """Elegant section header with a right-aligned footnote line."""
    note_html = f'<div class="section-note">* {escape(note)}</div>' if note else ""
    st.markdown(
        f"""
        <div class="section-head">
          <div class="section-title">{escape(title)}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

def begin_card():
    st.markdown('<div class="soft-card">', unsafe_allow_html=True)

def end_card():
    st.markdown('</div>', unsafe_allow_html=True)

def render_top_events_split(df, n=20, title="Top Events"):
    """Left: compact table of headlines. Right: one aggregate emotion bar."""
    if df is None or df.empty:
        render_section_header(title, "Headlines deduplicated by similarity; risk is modelled, not raw mentions.")
        st.info("No events in the selected window.")
        return

    show = df.copy().head(n)
    # choose time column and compute 'Age (min)'
    tcol = next((c for c in ["published","published_at","date","datetime","timestamp","time","ts"] if c in show.columns), None)
    if tcol:
        show["_dt"] = pd.to_datetime(show[tcol], errors="coerce", utc=True)
        now = pd.Timestamp.utcnow()
        show["Age (min)"] = ((now - show["_dt"]).dt.total_seconds() / 60.0).round(0)

    cols = st.columns([2.2, 1])  # left wide, right narrow

    with cols[0]:
        render_section_header(title, "Each row is a deduped event: Region · Topic · Risk · Source · Age.")
        tbl = show.rename(columns={
            "title":"Headline","risk_score":"Risk","topic":"Topic","region":"Region",
            "source":"Source","provider":"Source","site":"Source","domain":"Source","url":"Source Link"
        })
        keep = [c for c in ["Headline","Risk","Topic","Region","Source","Age (min)","Source Link"] if c in tbl.columns]
        tbl = tbl[keep]
        st.dataframe(
            tbl,
            use_container_width=True, hide_index=True, height=440,
            column_config={
                "Risk": st.column_config.NumberColumn(format="%.1f"),
                "Age (min)": st.column_config.NumberColumn(format="%.0f"),
                "Source Link": st.column_config.LinkColumn(display_text="Open")
            },
        )

    with cols[1]:
        render_section_header("Emotion Mix (Selected)", "Mean of Fear/Anger/Sadness vs Joy/Trust across listed headlines.")
        emo_cols = [f"emo_{k}" for k in ["fear","anger","sadness","joy","trust"]]
        for c in emo_cols:
            if c not in show.columns:
                show[c] = 0.0
        mix = [float(show[c].mean()) for c in emo_cols]
        fig = go.Figure(go.Bar(x=["Fear","Anger","Sadness","Joy","Trust"], y=mix))
        fig.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def render_reliability_panel(freshness: dict, src_counts: dict):
    """Clear, compact reliability readout with chips + table."""
    if not freshness:
        return
    # chips
    chips = []
    for key, meta in freshness.items():
        age = meta.get("age_min")
        count = meta.get("count", 0)
        if age is None:
            chips.append(f"{escape(key.title())}: {count} items")
        else:
            chips.append(f"{escape(key.title())}: {count} • {int(age)}m")
    st.markdown(
        '<div class="chip-row">' + " ".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>",
        unsafe_allow_html=True,
    )
    # table
    rows = []
    for name, meta in freshness.items():
        rows.append({
            "Feed": name,
            "Items": meta.get("count"),
            "Last Update (UTC)": str(meta.get("last_ts")) if meta.get("last_ts") is not None else "—",
            "Age (min)": meta.get("age_min") if meta.get("age_min") is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_event_cards_with_emotion(df, title, n=12):
    if df is None or df.empty:
        st.write("No events in window.")
        return
    st.subheader(title)
    show = df.head(n)
    cols = st.columns(3)
    for i, (_, row) in enumerate(show.iterrows()):
        with cols[i % 3]:
            st.markdown(f"**{row.get('title','')}**")
            meta = f"{row.get('region','Global')} · {row.get('topic','General')} · Risk {row.get('risk_score','—')}"
            st.caption(meta)
            emo = [row.get(f"emo_{k}",0.0) for k in ["fear","anger","sadness","joy","trust"]]
            efig = go.Figure(go.Bar(x=["Fear","Anger","Sadness","Joy","Trust"], y=emo))
            efig.update_layout(height=120, margin=dict(l=10,r=10,t=10,b=10), showlegend=False)
            st.plotly_chart(efig, use_container_width=True, config={"displayModeBar": False})
            url = row.get("url")
            if isinstance(url, str) and url:
                st.link_button("Open source", url)


def render_header():
    st.markdown("""
    <div style="padding:10px 6px 0 6px">
      <h2 style="margin-bottom:4px; font-weight:700; letter-spacing:.2px;">STRATEGIC <span style="color:#111">INTELLIGENCE WAR ROOM</span></h2>
      <div style="color:#666; font-size:13px; margin-top:-6px;">Professional global intelligence & movement tracking</div>
    </div>
    """, unsafe_allow_html=True)

def _kpi_card(title, value, subtitle=""):
    st.markdown(f"""
    <div style="border:1px solid #eee; border-radius:12px; padding:12px 14px; background:#fff;">
      <div style="font-size:12px; color:#777; text-transform:uppercase; letter-spacing:.6px;">{title}</div>
      <div style="font-size:28px; font-weight:700; margin-top:2px;">{value}</div>
      <div style="font-size:11px; color:#9aa;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_kpi_row(kpis: dict):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: _kpi_card("Intelligence Reports", kpis.get("total_reports", 0))
    with c2: _kpi_card("Movement Detections", kpis.get("movement", 0))
    with c3: _kpi_card("High-Risk Regions", kpis.get("high_risk_regions", 0))
    with c4: _kpi_card("Aircraft Tracked", kpis.get("aircraft", 0))
    with c5: _kpi_card("Average Risk Score", kpis.get("avg_risk", 0), "Composite signal")

def render_event_cards(df: pd.DataFrame, title="Top Events", n=12):
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No events in the selected filter window.")
        return
    cards = df.sort_values("risk", ascending=False).head(n)[["published_ts","region","topic","title","risk","sentiment","source","origin","link","cluster_size"]]
    cols = st.columns(3)
    i = 0
    for _, r in cards.iterrows():
        cluster = int(r.get("cluster_size") or 1)
        with cols[i % 3]:
            st.markdown(f"""
            <div style="border:1px solid #eee; border-radius:12px; padding:12px 14px; margin-bottom:12px; background:#fff;">
              <div style="font-size:11px; color:#777;">{r['region']} · {r['topic']} · {str(r['published_ts'])[:16]} UTC · x{cluster}</div>
              <div style="font-weight:700; margin:6px 0 8px 0; line-height:1.25">{r['title']}</div>
              <div style="font-size:12px; color:#666;">Risk {r['risk']} · Sentiment {round(r['sentiment'],2)} · {r['source']} ({r['origin']})</div>
              <div style="margin-top:8px;">
                <a href="{r['link']}" target="_blank" style="font-size:12px; text-decoration:none; border:1px solid #111; padding:6px 10px; border-radius:8px;">Open source</a>
              </div>
            </div>
            """, unsafe_allow_html=True)
        i += 1

def render_news_table(df: pd.DataFrame, title="Live Intelligence Feed"):
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No articles available at the moment.")
        return
    cols = ["published_ts","region","topic","title","risk","sentiment","source","origin","link"]
    st.dataframe(df[cols].sort_values("published_ts", ascending=False).head(400), use_container_width=True, height=560)

def render_markets(df: pd.DataFrame):
    st.markdown("#### Markets")
    if df is None or df.empty:
        st.info("No market data for the selected tickers.")
        return
    source_note = "polygon" if ("source" in df.columns and (df["source"] == "polygon").any()) else "yfinance"
    st.caption(f"Data source: {source_note}")
    c1, c2 = st.columns([1,2])
    with c1:
        show_cols = ["ticker","price","change_1d","volume"]
        if "source" in df.columns: show_cols.append("source")
        st.dataframe(df[show_cols], use_container_width=True, height=420)
    with c2:
        fig = px.bar(df, x="ticker", y="change_1d", title="Daily Change (%)")
        st.plotly_chart(fig, use_container_width=True)

def render_trends(df: pd.DataFrame):
    st.markdown("#### Google Trends — Rising Interest")
    if df is None or df.empty:
        st.info("No trend movement detected for the chosen topics.")
        return
    fig = px.bar(df, x="topic", y="value")
    st.plotly_chart(fig, use_container_width=True)

def render_regions_grid(df: pd.DataFrame, expanded: bool=False):
    if df is None or df.empty:
        st.info("No regional intelligence available right now.")
        return
    grouped = df.groupby(["region","topic"]).size().reset_index(name="reports").sort_values("reports", ascending=False)
    regions = grouped["region"].unique().tolist()
    for r in regions:
        st.markdown(f"##### {r}")
        sub = grouped[grouped["region"] == r].head(8)
        st.dataframe(sub, use_container_width=True, height=220)
        if expanded:
            st.markdown("**Latest in region**")
            st.dataframe(df[df["region"] == r][["published_ts","topic","title","risk","sentiment","source","origin","link"]].head(40),
                         use_container_width=True, height=360)

def render_feed_panel(news_df: pd.DataFrame, gdelt_df: pd.DataFrame):
    merged = news_df.copy()
    if gdelt_df is not None and not gdelt_df.empty:
        merged = pd.concat([news_df, gdelt_df], ignore_index=True).sort_values("published_ts", ascending=False)
    render_news_table(merged)

def render_reddit(df: pd.DataFrame):
    st.markdown("#### Reddit Signal")
    if df is None or df.empty:
        st.caption("Reddit credentials not configured or no results.")
        return
    st.dataframe(
        df[["created_utc","subreddit","title","score","url","query"]].sort_values("created_utc", ascending=False).head(150),
        use_container_width=True, height=480
    )
