import streamlit as st
import pandas as pd
import plotly.express as px

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
    with c3: _kpi_card("High‑Risk Regions", kpis.get("high_risk_regions", 0))
    with c4: _kpi_card("Aircraft Tracked", kpis.get("aircraft", 0))
    with c5: _kpi_card("Average Risk Score", kpis.get("avg_risk", 0), "Composite signal")

def render_news_table(df: pd.DataFrame, title="Live Intelligence Feed"):
    st.markdown(f"#### {title}")
    if df is None or df.empty:
        st.info("No articles available at the moment.")
        return
    cols = ["published_ts","region","topic","title","sentiment","source","origin","link"]
    dfv = df[cols].sort_values("published_ts", ascending=False).head(300)
    st.dataframe(dfv, use_container_width=True, height=560)

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
        if "source" in df.columns:
            show_cols.append("source")
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
            st.dataframe(df[df["region"] == r][["published_ts","topic","title","sentiment","source","origin","link"]].head(40),
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
