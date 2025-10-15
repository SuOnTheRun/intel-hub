# src/ui.py — refined UI components (lightweight, no extra deps)

import streamlit as st
import pandas as pd
import numpy as np
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

# ---------- Alert Ribbon ----------
def alert_ribbon(alerts: list, collapsed: bool = False, max_show: int = 18):
    """
    Displays alerts as elegant chips with subtle severity accents.
    """
    if not alerts:
        return

    def _badge(a):
        color = "#0f766e"  # default
        if a.kind in ("policy", "geo", "cyber"): color = "#334155"
        if a.severity >= 4: color = "#b91c1c"  # high risk
        if a.severity == 2: color = "#475569"
        bg = "rgba(0,0,0,0.04)"
        link = f"<a href='{a.link}' target='_blank' style='text-decoration:none;color:#0b132b'>" if a.link else "<span>"
        end = "</a>" if a.link else "</span>"
        return f"""
        <span style="
          display:inline-flex;align-items:center;gap:8px;
          padding:6px 10px;margin:6px 6px 0 0;border-radius:999px;
          background:{bg};border:1px solid #e5e7eb;">
          <span style="width:8px;height:8px;border-radius:999px;background:{color};"></span>
          <strong style="font-size:12px;color:#0b1221">{a.title}</strong>
          {link}<span style="font-size:12px;color:#475569">{a.detail}</span>{end}
        </span>
        """

    chips = "".join(_badge(a) for a in alerts[:max_show])
    block = f"""
    <div style="
      margin:14px 0 8px 0;padding:10px 12px;border-radius:14px;
      background:linear-gradient(180deg,#ffffff 0%,#f9fafb 100%);border:1px solid #e6e8ec;">
      {chips}
    </div>
    """
    if collapsed:
        with st.expander("Alerts"):
            st.markdown(block, unsafe_allow_html=True)
    else:
        st.markdown(block, unsafe_allow_html=True)

# ---------- helpers ----------
def _safe_mean(s: pd.Series, default=0.0):
    try:
        return float(s.mean())
    except Exception:
        return default

def _fmt_delta(x: float) -> str:
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.2f}"

# ---------- KPI ribbon ----------
def kpi_ribbon(heat_df: pd.DataFrame, tension_df: pd.DataFrame, news_df: pd.DataFrame):
    df = heat_df.copy()
    if not tension_df.empty:
        df = df.merge(tension_df[["category","tension_0_100"]], on="category", how="left")

    market_move = _safe_mean(df["market_pct"])
    news_momentum = _safe_mean(df["news_z"])
    interest = _safe_mean(df["trends"])
    if news_df is not None and not news_df.empty and "sentiment" in news_df.columns:
        negativity = float((news_df["sentiment"] < -0.2).mean()) * 100.0
        headline_tone = float(news_df["sentiment"].mean())
    else:
        negativity, headline_tone = 0.0, 0.0
    tension = _safe_mean(df.get("tension_0_100", pd.Series([0])))

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Market Move (5d %)", f"{market_move:.2f}")
    c2.metric("News Momentum (z)", f"{news_momentum:.2f}")
    c3.metric("Public Interest (Trends)", f"{interest:.1f}")
    c4.metric("Negativity Density (%)", f"{negativity:.1f}")
    c5.metric("Headline Tone (−1…+1)", f"{headline_tone:.2f}")
    c6.metric("Tension Index (0–100)", f"{tension:.1f}")

    with st.expander("What do these indicators mean?"):
        st.markdown(
            """
            - **Market Move (5d %)** — Average five-day percent change across each category’s mapped tickers/ETFs. Higher is better.  
            - **News Momentum (z)** — How unusually busy the news flow is (z-score of volume) over 24–72h. Positive = busier than usual.  
            - **Public Interest (Trends)** — Google Trends (0–100) averaged across search terms per category. Higher = more public attention.  
            - **Negativity Density (%)** — Share of headlines with negative tone (compound < −0.2). Lower is better.  
            - **Headline Tone (−1…+1)** — Average tone of headlines; near 0 = mixed, positive = supportive, negative = risk-off.  
            - **Tension Index (0–100)** — Composite risk signal from negativity, drawdown, tone volatility, news, trends, and entity intensity. Higher = more tension.
            """
        )

# ---------- Executive highlights ----------
def highlights_panel(heat_df: pd.DataFrame, tension_df: pd.DataFrame):
    if heat_df.empty:
        return
    df = heat_df.copy()
    high_tension = None
    if not tension_df.empty and "tension_0_100" in tension_df:
        high_tension = tension_df.sort_values("tension_0_100", ascending=False).head(1)
    top_momentum = df.sort_values("news_z", ascending=False).head(1)
    most_negative = df.sort_values("sentiment", ascending=True).head(1)
    biggest_move = df.iloc[[df["market_pct"].abs().argmax()]] if len(df) else df.head(0)
    top_interest = df.sort_values("trends", ascending=False).head(1)

    st.subheader("Highlights")
    col = st.columns(5)
    col[0].metric("Top News Momentum", f"{top_momentum['category'].values[0] if len(top_momentum) else '—'}",
                  _fmt_delta(float(top_momentum['news_z'].values[0])) if len(top_momentum) else "0.00")
    col[1].metric("Highest Tension", f"{high_tension['category'].values[0] if (high_tension is not None and len(high_tension)) else '—'}",
                  f"{float(high_tension['tension_0_100'].values[0]):.1f}" if (high_tension is not None and len(high_tension)) else "0.0")
    col[2].metric("Most Negative Tone", f"{most_negative['category'].values[0] if len(most_negative) else '—'}",
                  f"{float(most_negative['sentiment'].values[0]):.2f}" if len(most_negative) else "0.00")
    col[3].metric("Biggest Market Move", f"{biggest_move['category'].values[0] if len(biggest_move) else '—'}",
                  f"{float(biggest_move['market_pct'].values[0]):.2f}%")
    col[4].metric("Interest Spike", f"{top_interest['category'].values[0] if len(top_interest) else '—'}",
                  f"{float(top_interest['trends'].values[0]):.1f}" if len(top_interest) else "0.0")

# ---------- Executive Summary ----------
def _label_tone(v: float) -> str:
    if v >= 0.15: return "supportive tone"
    if v <= -0.15: return "adverse tone"
    return "mixed tone"

def _label_move(v: float) -> str:
    if v >= 1.0: return "a short-term rally"
    if v <= -1.0: return "a short-term pullback"
    return "little market movement"

def _label_news(z: float) -> str:
    if z >= 1.0: return "elevated news momentum"
    if z <= -1.0: return "quiet newsflow"
    return "normal newsflow"

def _label_trends(v: float) -> str:
    if v >= 60: return "heightened public interest"
    if v <= 30: return "muted public interest"
    return "steady public interest"

def _top_driver(news_df: pd.DataFrame, category: str) -> str:
    g = news_df[news_df["category"] == category].sort_values("published_dt", ascending=False)
    if g.empty: return ""
    r = g.iloc[0]
    return f' — on account of: “[{r["title"]}]({r["link"]})” ({r["source"]})'

def _interesting_score(row) -> float:
    return abs(float(row.get("news_z", 0))) + abs(float(row.get("market_pct", 0))) / 2.0 + abs(float(row.get("sentiment", 0))) + float(row.get("tension_0_100", 0)) / 50.0

def insights_summary(heat_df: pd.DataFrame, news_df: pd.DataFrame, tension_df: pd.DataFrame, max_items: int = 8):
    if heat_df.empty:
        st.caption("No data available for a summary yet.")
        return
    df = heat_df.copy()
    if not tension_df.empty:
        df = df.merge(tension_df[["category","tension_0_100"]], on="category", how="left")
    else:
        df["tension_0_100"] = np.nan

    df["__score__"] = df.apply(_interesting_score, axis=1)
    df = df.sort_values("__score__", ascending=False).head(max_items)

    for _, r in df.iterrows():
        cat = str(r["category"])
        parts = [
            _label_news(float(r.get("news_z", 0))),
            _label_tone(float(r.get("sentiment", 0))),
            _label_move(float(r.get("market_pct", 0))),
            _label_trends(float(r.get("trends", 0))),
        ]
        parts = [p for p in parts if p not in ("normal newsflow","steady public interest")]
        clause = " and ".join(parts[:2]) + (", " + ", ".join(parts[2:]) if len(parts) > 2 else "")
        tension = r.get("tension_0_100", np.nan)
        tension_txt = f" (Tension: {float(tension):.0f})" if pd.notna(tension) else ""
        driver = _top_driver(news_df, cat)
        st.markdown(f"- **{cat}** shows {clause}{tension_txt}{driver}")

# ---------- Heatmap (labeled) ----------
def heatmap_labeled(df: pd.DataFrame):
    if df.empty:
        st.info("No category signals yet.")
        return
    show = df[["category","news_z","sentiment","market_pct","trends"]].copy()
    show = show.set_index("category").rename(columns={
        "news_z":"News Momentum (z)",
        "sentiment":"Headline Tone (−1…+1)",
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

# ---------- Headlines overview ----------
def headlines_overview(news_df: pd.DataFrame, per_page: int = 12):
    if news_df.empty:
        st.caption("No headlines available.")
        return
    cats = ["All"] + sorted(news_df["category"].dropna().unique().tolist())
    col1, col2 = st.columns([2,1])
    sel_cat = col1.selectbox("Filter by category", cats, index=0)
    total = len(news_df) if sel_cat == "All" else len(news_df[news_df["category"] == sel_cat])
    page = col2.number_input(f"Page (total {max(1, (total + per_page - 1) // per_page)})", min_value=1, step=1, value=1)
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

# ---------- Narratives & Tension ----------
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
            "sent_vol":"Tone Volatility",
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
    avg = float(heat_df["sentiment"].mean()) if "sentiment" in heat_df else 0.0
    neg_share = float((news_df["sentiment"] < -0.2).mean()) if not news_df.empty else 0.0

    verdict = "Balanced"
    if avg >= 0.15 and neg_share < 0.30:
        verdict = "Constructive"
    elif avg <= -0.15 or neg_share > 0.45:
        verdict = "Adverse"

    st.subheader("How to read this sentiment")
    st.markdown(
        f"""
        **Current read:** *{verdict}*.  
        - Average headline tone: **{avg:.2f}** (−1 to +1).  
        - Share of clearly negative headlines: **{neg_share*100:.1f}%** (threshold 0.2).  

        **Interpretation**
        - **Constructive** — supportive tone; lean into momentum and fresh proof points.  
        - **Balanced** — mixed tone; emphasize credibility; avoid polarizing claims.  
        - **Adverse** — risk-off mood; stress value, safety, reassurance; pause risky launches unless supported.
        """
    )

# ---------- Glossary ----------
def glossary_panel(show_full: bool = False):
    st.subheader("Glossary")
    st.markdown(
        """
        - **Market Move (5d %)** — Average five-day percent change across proxy tickers/ETFs per category. Higher is better.  
        - **News Momentum (z)** — Z-score of story count by category over the last 24–72h. Positive = busier than usual.  
        - **Public Interest (Trends)** — Google Trends (0–100) across category keywords. Higher = more public attention.  
        - **Negativity Density** — Fraction of headlines with compound score < −0.2. Lower is better.  
        - **Headline Tone (−1…+1)** — Mean compound tone of headlines (lexicon-based on this build).  
        - **Tension Index (0–100)** — Composite of negativity, market drawdown, tone volatility, news volume, search interest, and entity intensity. Higher = more tension.  
        """
    )
    if show_full:
        st.markdown(
            """
            **Method Notes**
            - Tone model: lexicon-based compound score (upgrade path to transformer).  
            - News Momentum: per-category 24–72h counts standardized (z).  
            - Trends: Google Trends 7-day interest across category keywords.  
            - Tension weights: Neg 25%, Drawdown 20%, Volatility 20%, News 15%, Trends 10%, Entities 10%.  
            """
        )
