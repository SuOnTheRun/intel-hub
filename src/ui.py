import streamlit as st
import plotly.express as px
import pandas as pd

def kpi_cards(df):
    c1, c2, c3 = st.columns(3)
    c1.metric("Composite (Tech)", f"{df.loc[df['category']=='Technology','composite'].mean():.2f}")
    c2.metric("Sentiment (Tech)", f"{df.loc[df['category']=='Technology','sentiment'].mean():.2f}")
    c3.metric("News volume z (Tech)", f"{df.loc[df['category']=='Technology','news_z'].mean():.2f}")

def heatmap(df):
    show = df[["category","news_z","sentiment","market_pct"]].copy()
    show = show.set_index("category").rename(columns={"news_z":"News z","sentiment":"Sentiment","market_pct":"Market %"})
    fig = px.imshow(show, aspect="auto", labels=dict(x="Signal", y="Category", color="Value"))
    st.plotly_chart(fig, use_container_width=True)

def headlines_section(blocks: dict):
    st.subheader("Top Headlines by Category")
    for cat in blocks:
        st.markdown(f"**{cat}**")
        g = blocks[cat]
        if g.empty:
            st.caption("No matching headlines right now.")
            continue
        for _, r in g.iterrows():
            st.markdown(f"- [{r['title']}]({r['link']})  \n  <span style='color:#6b7280;font-size:12px'>{r['source']} — {r['published_dt'].strftime('%d %b %Y %H:%M')}</span>", unsafe_allow_html=True)
