import os, pandas as pd, streamlit as st, plotly.express as px, yfinance as yf
from dateutil import tz
from datetime import datetime
from src.theming import inject_css, kpi
from src.collectors import (
    REGIONS, TOP_MARKETS, CATEGORIES,
    fetch_news, fetch_quotes, fetch_trends,
    news_z_dynamic, senti_avg, emotion_avg, ccs_simple, estimated_feed_size
)
from src.secrets import REDDIT

st.set_page_config(page_title="Intelligence Hub", layout="wide")
inject_css()
IST = tz.gettz("Asia/Kolkata")

st.sidebar.markdown("### Intelligence Hub")
page = st.sidebar.radio("", ["Command Center","Regions","Categories","Markets","Social","My Data","Methods"], label_visibility="collapsed")
st.sidebar.markdown("---")
st.sidebar.caption("Updated: " + datetime.now(IST).strftime("%d %b %Y, %H:%M IST"))

def region_country_controls():
    c1, c2 = st.columns([1,1])
    with c1: region = st.selectbox("Region", ["—"] + list(REGIONS.keys()) + TOP_MARKETS, index=0)
    with c2:
        choices = ["—"]
        if region in REGIONS: choices += REGIONS[region]
        elif region in TOP_MARKETS: choices = ["—", region]
        country = st.selectbox("Country", choices, index=0)
    return (None if region=="—" else region), (None if country=="—" else country)

def category_select():
    return st.selectbox("Category", list(CATEGORIES.keys()), format_func=lambda k: CATEGORIES[k]["name"])

@st.cache_data(ttl=300, show_spinner=False)
def _news(cat, country, region): return fetch_news(cat, country, region)

@st.cache_data(ttl=300, show_spinner=False)
def _quotes(symbols): return fetch_quotes(symbols)

@st.cache_data(ttl=300, show_spinner=False)
def _trends(cat, geo): return fetch_trends(cat, geo)

def sentiment_hist(headlines):
    if not headlines: return
    df = pd.DataFrame([h["senti"] for h in headlines], columns=["sentiment"])
    fig = px.histogram(df, x="sentiment", nbins=24)
    st.plotly_chart(fig, use_container_width=True)

def emotion_bar(emotions: dict):
    if not emotions: return
    df = pd.DataFrame({"emotion": list(emotions.keys()), "share": list(emotions.values())})
    fig = px.bar(df, x="emotion", y="share")
    st.plotly_chart(fig, use_container_width=True)

def source_mix(headlines):
    if not headlines: return
    df = pd.DataFrame(headlines)
    mix = df["source"].value_counts().reset_index()
    mix.columns=["source","count"]
    fig = px.bar(mix, x="source", y="count")
    st.plotly_chart(fig, use_container_width=True)

# ------- PAGES --------
if page == "Command Center":
    st.header("Command Center")
    st.caption("Global pulse across categories from BBC / Al Jazeera / AP / DW / CNBC / FT / Reuters + NewsAPI; markets via Yahoo Finance.")

    feed_n = estimated_feed_size()
    tech = _news("technology", None, None)
    nz = news_z_dynamic(tech, feed_n); sa = senti_avg(tech)
    q = _quotes(CATEGORIES["technology"]["tickers"]); mkt = (q[0]["pct"] if q else 0.0)

    c1,c2,c3 = st.columns(3)
    with c1: kpi("Composite (Tech)", f"{ccs_simple(nz, sa, None, mkt):.2f}")
    with c2: kpi("Sentiment (Tech)", f"{sa:.2f}")
    with c3: kpi("News volume z (Tech)", f"{nz:.2f}")

    st.subheader("Category Heatmap (24–72h)")
    rows=[]
    for slug,cfg in CATEGORIES.items():
        news=_news(slug,None,None); q=_quotes(cfg["tickers"])
        rows.append({"Category":cfg["name"],"News z":news_z_dynamic(news,feed_n),"Sentiment":senti_avg(news),"Market Δ%": q[0]["pct"] if q else 0.0})
    st.dataframe(pd.DataFrame(rows).set_index("Category"))

    st.subheader("Top Headlines by Category")
    for slug,cfg in CATEGORIES.items():
        items=_news(slug,None,None)[:8]
        st.markdown(f"**{cfg['name']}**")
        if not items: st.caption("No matching headlines right now."); continue
        for h in items:
            st.write(f"- [{h['title']}]({h['link']}) — {h['source']} · Sent {h['senti']:.2f}")

elif page == "Regions":
    st.header("Regions")
    region, country = region_country_controls()
    cat = category_select()
    feed_n = estimated_feed_size()

    left, right = st.columns([1.3, 0.7])
    with left:
        st.subheader("News & Sentiment")
        headlines = _news(cat, country, region)
        nz = news_z_dynamic(headlines, feed_n); sa = senti_avg(headlines)
        c1,c2 = st.columns(2)
        with c1: kpi("News z", f"{nz:.2f}")
        with c2: kpi("Sentiment", f"{sa:.2f}")
        if headlines:
            df=pd.DataFrame(headlines)[["title","source","published","senti","link"]]
            st.dataframe(df, hide_index=True)
            st.markdown("**Sentiment distribution**"); sentiment_hist(headlines)
            st.markdown("**Emotion mix**"); emotion_bar(emotion_avg(headlines))
            st.markdown("**Source mix**"); source_mix(headlines)
        else:
            st.caption("No matching headlines for this scope.")

    with right:
        st.subheader("Market Pulse")
        q=_quotes(CATEGORIES[cat]["tickers"])
        if q: st.dataframe(pd.DataFrame(q), hide_index=True)
        st.subheader("Search Interest (90 days)")
        geo = country or region or "IN"
        try:
            ts = _trends(cat, geo)
            for d in ts["datasets"]:
                fig = px.line(pd.DataFrame({"date": ts["labels"], d["label"]: d["data"]}), x="date", y=d["label"])
                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.caption("Trends not available for this scope right now.")

elif page == "Categories":
    st.header("Categories")
    region, country = region_country_controls()
    cat = category_select()
    feed_n = estimated_feed_size()
    headlines = _news(cat, country, region)
    nz=news_z_dynamic(headlines,feed_n); sa=senti_avg(headlines)
    q=_quotes(CATEGORIES[cat]["tickers"]); pct=q[0]["pct"] if q else 0.0

    c1,c2,c3 = st.columns(3)
    with c1: kpi("News z", f"{nz:.2f}")
    with c2: kpi("Sentiment", f"{sa:.2f}")
    with c3: kpi("Market Δ%", f"{pct:.2f}%")

    st.markdown("**News**")
    if headlines:
        df=pd.DataFrame(headlines)[["title","source","published","senti","link"]]
        st.dataframe(df, hide_index=True)
        colA,colB = st.columns(2)
        with colA:
            st.markdown("**Sentiment distribution**"); sentiment_hist(headlines)
            st.markdown("**Source mix**"); source_mix(headlines)
        with colB:
            st.markdown("**Emotion mix**"); emotion_bar(emotion_avg(headlines))
            terms = pd.Series(" ".join([h["title"] for h in headlines]).lower().split()).value_counts().head(20)
            st.markdown("**Top terms**")
            st.write(", ".join([t for t in terms.index if len(t)>3]))
    else:
        st.caption("No matching stories right now.")

elif page == "Markets":
    st.header("Markets & Media Conditions")
    rows=[]
    for slug,cfg in CATEGORIES.items():
        q=_quotes(cfg["tickers"])
        if q: rows.extend(q)
    if rows:
        st.dataframe(pd.DataFrame(rows).drop_duplicates(subset=["symbol"]).set_index("symbol"))
    st.caption("Add FX/commodities via yfinance tickers (EURUSD=X, GBPUSD=X, CL=F, GC=F, etc.).")

elif page == "Social":
    st.header("Social & Community Pulse")
    if all(REDDIT.values()) and REDDIT["client_id"]:
        import praw
        reddit = praw.Reddit(**REDDIT)
        subs = ["worldnews","technology","business"]
        posts=[]
        for s in subs:
            for p in reddit.subreddit(s).top(time_filter="day", limit=10):
                posts.append({"subreddit": str(p.subreddit), "title": p.title, "score": int(p.score), "url": f"https://www.reddit.com{p.permalink}"})
        st.dataframe(pd.DataFrame(posts), hide_index=True)
    else:
        st.caption("Add Reddit credentials to enable this page.")

elif page == "My Data":
    st.header("My Data — Plug & View")
    f = st.file_uploader("Upload CSV or Excel", type=["csv","xlsx"])
    if f:
        name=f.name.lower()
        if name.endswith(".csv"):
            df=pd.read_csv(f); st.dataframe(df.head(50))
        else:
            xls=pd.ExcelFile(f); st.write("Sheets:", xls.sheet_names)
            for s in xls.sheet_names[:3]:
                df=pd.read_excel(xls,s); st.write(f"Preview — {s}"); st.dataframe(df.head(50))
        st.success("Preview complete. Say “add ingest” and I’ll wire SQLite storage + overlays.")

else:
    st.header("Methods & Data Quality")
    st.markdown("""
**Open sources**: BBC / Al Jazeera / AP / DW / CNBC / FT / Reuters (RSS) + NewsAPI, Yahoo Finance (`yfinance`), Google Trends (`pytrends`).  
**Refresh**: cache TTL ≈ 5 minutes.  
**Sentiment**: VADER on titles. **Emotions**: NRC lexicon (open) on titles/briefs.  
**News z**: dynamic baseline from feed size (no hard-coded constants).  
""")
