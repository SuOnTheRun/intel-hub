import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px

def render_sources_sidebar():
    st.caption("News: Reuters, AP, NPR, CNBC, TechCrunch, The Verge, etc.")
    st.caption("Regulatory: SEC, FTC, FDA, FCC.")
    st.caption("Signals: Google Trends, TSA throughput, Yahoo Finance.")
    st.caption("Social: curated subreddit RSS.")

def _timeseries(df: pd.DataFrame, x: str, y: str, title: str):
    if df.empty:
        st.info("No data")
        return
    fig = px.line(df, x=x, y=y, title=None)
    st.plotly_chart(fig, use_container_width=True)

def render_command_center(kpis, risk, news, trends, stocks, mobility, ent_df, topics):
    c1, c2, c3 = st.columns((1,1,1))
    with c1:
        st.subheader("Tension Index")
        st.dataframe(risk.sort_values("tension_index", ascending=False), use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Category Coverage")
        st.dataframe(kpis.sort_values("news_items", ascending=False), use_container_width=True, hide_index=True)
    with c3:
        st.subheader("Market Movers (Today)")
        st.dataframe(stocks[["ticker","price","pct","volume"]].head(10), use_container_width=True, hide_index=True)

    st.markdown("### Trend Momentum (Google Trends)")
    if not trends.empty:
        _timeseries(trends.reset_index().melt(id_vars=["timestamp"], var_name="kw", value_name="score")[["timestamp","score"]], "timestamp","score","Trends")

    st.markdown("### Latest Headlines")
    st.dataframe(news[["published_dt","title","source","link"]].head(40), use_container_width=True, hide_index=True)

    st.markdown("### Entity Surface (Top mentions)")
    if not ent_df.empty:
        top = ent_df["entity"].value_counts().head(30).reset_index()
        top.columns = ["entity","count"]
        st.dataframe(top, use_container_width=True, hide_index=True)

    st.markdown("### Narrative Clusters (representative terms)")
    if not topics.empty:
        sample = topics.groupby("cluster").head(6).reset_index(drop=True)
        st.dataframe(sample[["cluster","term","weight","sample"]], use_container_width=True, hide_index=True)

def render_category_page(selected, news, social, trends, ent_df, topics):
    for cat in selected:
        st.markdown(f"## {cat}")
        n = news[news["title"].str.contains(cat, case=False, na=False)]
        s = social[social["title"].str.contains(cat, case=False, na=False)]
        t = trends  # already scoped by payload
        e = ent_df[ent_df["text"].str.contains(cat, case=False, na=False)]
        st.markdown("**News**")
        st.dataframe(n[["published_dt","title","source","link","sentiment"]].head(50), use_container_width=True, hide_index=True)
        st.markdown("**Community Pulse**")
        st.dataframe(s[["published_dt","title","source","link","sentiment"]].head(50), use_container_width=True, hide_index=True)
        st.markdown("**Entities**")
        top_e = e["entity"].value_counts().head(20).reset_index()
        top_e.columns = ["entity","count"]
        st.dataframe(top_e, use_container_width=True, hide_index=True)
