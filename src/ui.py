# src/ui.py — refined UI components for Intelligence Hub (no extra deps)

import streamlit as st
import pandas as pd
import plotly.express as px

# ---------- Luxury header ----------
def luxe_header(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div style="
            padding: 18px 22px;
            border-radius: 18px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e6e8ec;
            box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
        ">
          <div style="font-weight:800; font-size:34px; letter-spacing:-0.02em; color:#0B1221;">
            {title}
          </div>
          <div style="margin-top:6px; font-size:14px; color:#5e6673;">
            {subtitle}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- KPI ribbon ----------
def _safe_mean(s: pd.Series, default=0.0):
    try:
        return float(s.mean())
    except Exception:
        return default

def kpi_ribbon(heat_df: pd.DataFrame, tension_df: pd.DataFrame):
    """
    Shows six intuitive indicators:
      1) Market Move (avg 5d %)
      2) News Momentum (z of volume)
      3) Public Interest (Google Trends)
      4) Negativity Density (% of headlines < -0.2)
      5) Sentiment (avg compound)
      6) Tension Index (0–100)
    """
    # join for access
    df = heat_df.copy()
    if not tension_df.empty:
        df = df.merge(tension_df[["category","tension_0_100","neg_density"]], on="category", how="left")
    # "All categories" aggregates
    market_move = _safe_mean(df["market_pct"])
    news_momentum = _safe_mean(df["news_z"])
    interest = _safe_mean(df["trends"])
    negativity = _safe_mean(df["neg_density"]) if "neg_density" in df else 0.0
    sentiment = _safe_mean(df["sentiment"])
    tension = _safe_mean(df["tension_0_100"]) if "tension_0_100" in df else 0.0

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Market Move (5d %)", f"{market_move:.2f}")
    c2.metric("News Momentum (z)", f"{news_momentum:.2f}")
    c3.metric("Public Interest (Trends)", f"{interest:.1f}")
    c4.metric("Negativity Density (%)", f"{negativity*100:.1f}")
    c5.metric("Sentiment (−1…+1)", f"{sentiment:.2f}")
    c6.metric("Tension Index (0–100)", f"{tension:.1f}")

    with st.expander("What do these indicators mean?"):
        st.markdown(
            """
            - **Market Move (5d %)** — Average five-day percent change across each category’s proxy tickers/ETFs.  
            - **News Momentum (z)** — Z-score of story volume vs other categories in the last 24–72h. Positive = unusually busy.  
            - **Public Interest (Trends)** — Google Trends (0–100) averaged across search terms per category.  
            - **Negativity Density (%)** — Share of headlines with negative sentiment (< −0.2).  
            - **Sentiment (−1…+1)** — Mean compound sentiment of headlines (VADER on this build).  
            - **Tension Index (0–100)** — Composite risk read (negativity, drawdown, volatility, news, trends, entities).
            """
        )


# ---------- Heatmap (labeled) ----------
def heatmap_labeled(df: pd.DataFrame):
    if df.empty:
        st.info("No category signals yet.")
        return
    show = df[["category","news_z","sentiment","market_pct","trends"]].copy()
    show = show.set_index("category").rename(columns={
        "news_z":"News Momentum (z)",
        "sentiment":"Sentiment (−1…+1)",
        "market_pct":"Market Move (5d %)",
        "trends":"Public Interest (Trends)"
    })
    fig = px.imshow(
        show,
        aspect="auto",
        color_continuous_scale="RdBu",
        origin="lower",
        labels=dict(x="Signal", y="Category", color="Value"),
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)


# ---------- Headlines overview (paged + filterable) ----------
def headlines_overview(news_df: pd.DataFrame, per_page: int = 12):
    if news_df.empty:
        st.caption("No headlines available.")
        return
    cats = ["All"] + sorted(news_df["category"].dropna().unique().tolist())
    col1, col2 = st.columns([2,1])
    sel_cat = col1.selectbox("Filter by category", cats, index=0)
    total = len(news_df) if sel_cat == "All" else len(news_df[news_df["category"] == sel_cat])
    page = col2.number_input("Page", min_value=1, step=1, value=1)
    start = (int(page) - 1) * per_page
    end = start + per_page

    df = news_df if sel_cat == "All" else news_df[news_df["category"] == sel_cat]
    df = df.sort_values("published_dt", ascending=False).iloc[start:end]

    for _, r in df.iterrows():
        st.markdown(
            f"""**{r['category']} · {r['source']}** — [{r['title']}]({r['link']})  
            <span style='color:#6b7280;font-size:12px'>{r['published_dt'].strftime('%d %b %Y %H:%M')}</span>""",
            unsafe_allow_html=True
        )


# ---------- Narratives & Tension (already present) ----------
def narratives_panel(narr_table: pd.DataFrame, top_docs: dict):
    st.subheader("Narratives & Key Themes")
    if narr_table.empty:
        st.caption("No narratives detected yet.")
        return
    st.dataframe(
        narr_table[["category","narrative","n_docs","weight"]]
        .assign(**{"Weight %": (narr_table["weight"]*100).round(1)})[
            ["category","narrative","n_docs","Weight %"]
        ],
        use_container_width=True
    )
    with st.expander("Representative Headlines by Category"):
        for cat, g in top_docs.items():
            st.markdown(f"**{cat}**")
            if g.empty:
                st.caption("No samples.")
                continue
            for _, r in g.iterrows():
                st.markdown(f"- [{r['title']}]({r['link']})")
            st.markdown("---")

def tension_panel(tension_df: pd.DataFrame):
    st.subheader("Tension Index (0–100)")
    if tension_df.empty:
        st.caption("No tension signals available.")
        return
    st.dataframe(
        tension_df[["category","tension_0_100","neg_density","sent_vol","news_z","market_drawdown","trends_norm","entity_intensity"]]
        .rename(columns={
            "tension_0_100":"Tension",
            "neg_density":"Negativity (%)",
            "sent_vol":"Sent Volatility",
            "news_z":"News z",
            "market_drawdown":"Mkt Drawdown",
            "trends_norm":"Trends (norm)",
            "entity_intensity":"Entity Intensity"
        }),
        use_container_width=True
    )


# ---------- Sentiment interpretation ----------
def sentiment_explainer(heat_df: pd.DataFrame, news_df: pd.DataFrame):
    if heat_df.empty:
        return
    st.subheader("How to read this sentiment")
    avg = float(heat_df["sentiment"].mean()) if "sentiment" in heat_df else 0.0
    neg_share = float((news_df["sentiment"] < -0.2).mean()) if not news_df.empty else 0.0

    verdict = "balanced"
    if avg >= 0.15 and neg_share < 0.30:
        verdict = "constructive"
    elif avg <= -0.15 or neg_share > 0.45:
        verdict = "adverse"

    st.markdown(
        f"""
        **Current read:** *{verdict.capitalize()}*.  
        - Average headline sentiment: **{avg:.2f}** (range −1…+1; VADER).  
        - Share of notably negative headlines: **{neg_share*100:.1f}%** (threshold 0.2).  

        **Interpretation guide**
        - **Constructive**: broadly supportive tone; consider leaning into momentum and testing bolder messaging.  
        - **Balanced**: mixed tone; use proof points and credible signals; avoid polarizing claims.  
        - **Adverse**: risk-off mood; emphasize reassurance, value, and safety—avoid risky launches without supporting evidence.
        """
    )


# ---------- Glossary ----------
def glossary_panel(show_full: bool = False):
    st.subheader("Glossary")
    st.markdown(
        """
        - **Market Move (5d %)** — Average five-day percent change across proxy tickers/ETFs per category.  
        - **News Momentum (z)** — Z-score of story count by category over the last 24–72h.  
        - **Public Interest (Trends)** — Google Trends (0–100) averaged over configured terms.  
        - **Negativity Density** — Fraction of headlines with compound sentiment < −0.2.  
        - **Sentiment (−1…+1)** — Mean compound sentiment of headlines (VADER on lightweight build).  
        - **Tension Index (0–100)** — Composite of negativity, market drawdown, sentiment volatility, news volume, search interest, and entity intensity.  
        """)
    if show_full:
        st.markdown(
            """
            **Method Notes**
            - Sentiment: VADER (rule-based) with transformer upgrade path when infra allows.  
            - News Momentum: per-category counts → standardized (z).  
            - Trends: Google Trends interest over 7d across category keywords.  
            - Tension: weighted blend (neg 25%, drawdown 20%, volatility 20%, news 15%, trends 10%, entities 10%).  
            """
        )
