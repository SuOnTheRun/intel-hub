import streamlit as st
import pandas as pd
import plotly.express as px

def markets_block(df: pd.DataFrame):
    if df.empty:
        st.info("No market data returned for the chosen tickers.")
        return
    c1, c2 = st.columns([1,2])
    with c1:
        st.dataframe(df, use_container_width=True)
    with c2:
        fig = px.bar(df, x="ticker", y="change_1d", title="Daily Change (%)")
        st.plotly_chart(fig, use_container_width=True)

def news_block(df: pd.DataFrame):
    if df.empty:
        st.info("No RSS articles fetched.")
        return
    st.dataframe(df[["source","published_ts","title","sentiment","link"]], use_container_width=True, height=420)

def trends_block(df: pd.DataFrame):
    if df.empty:
        st.info("No Google Trends signal for the topics right now.")
        return
    fig = px.bar(df, x="topic", y="value", title="Rising Interest (last 7 days)")
    st.plotly_chart(fig, use_container_width=True)

def mobility_block(df: pd.DataFrame):
    if df.empty:
        st.info("No aircraft in the region at this moment (or API limited).")
        return
    st.dataframe(
        df[["callsign","origin_country","latitude","longitude","velocity","true_track","geo_altitude"]],
        use_container_width=True, height=420
    )

def reddit_block(df: pd.DataFrame):
    if df.empty:
        st.caption("Reddit credentials not configured or no results.")
        return
    st.dataframe(df[["query","subreddit","title","score","url","created_utc"]].sort_values("created_utc", ascending=False),
                 use_container_width=True, height=420)
