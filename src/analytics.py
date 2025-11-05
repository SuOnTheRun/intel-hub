# src/analytics.py — cross-sectional momentum + composite
from __future__ import annotations
import pandas as pd
import numpy as np

def _robust_z(counts: pd.Series) -> pd.Series:
    """
    Cross-sectional z using robust MAD. Works even on a single snapshot.
    """
    x = counts.astype(float)
    med = x.median()
    mad = (x - med).abs().median()
    if mad == 0:
        # fallback to std if MAD collapses
        std = x.std(ddof=0)
        return (x - x.mean()) / (std if std > 1e-9 else 1.0)
    return 0.6745 * (x - med) / (mad if mad > 1e-9 else 1.0)

def build_category_heatmap(news_df: pd.DataFrame, base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns one row per category with:
      category, news_count, news_z, sentiment, market_pct, trends, composite
    Works even if some categories have few/zero items.
    """
    # counts & tone
    if news_df is None or news_df.empty:
        core = pd.DataFrame(columns=["category","news_count","sentiment"])
    else:
        g = news_df.groupby("category", dropna=True)
        core = pd.DataFrame({
            "news_count": g.size(),
            "sentiment": g["sentiment"].mean()
        }).reset_index()

    # base metrics (trends, market) may be empty — make safe defaults
    if base_df is None or base_df.empty:
        base_df = pd.DataFrame(columns=["category","trends","market_pct"])
    if "trends" not in base_df: base_df["trends"] = np.nan
    if "market_pct" not in base_df: base_df["market_pct"] = 0.0

    # union of categories from both sources
    cats = pd.DataFrame({"category": pd.unique(pd.concat([core["category"], base_df["category"]], ignore_index=True).dropna())})

    out = cats.merge(core, on="category", how="left").merge(base_df[["category","trends","market_pct"]], on="category", how="left")
    out["news_count"] = out["news_count"].fillna(0).astype(int)
    out["sentiment"]  = out["sentiment"].fillna(0.0).astype(float)
    out["trends"]     = out["trends"].fillna(0.0).astype(float)
    out["market_pct"] = out["market_pct"].fillna(0.0).astype(float)

    # cross-sectional momentum from current snapshot
    out["news_z"] = _robust_z(out["news_count"])

    # simple composite (you already show details elsewhere)
    # weights: momentum 35%, tone 25%, market 20%, interest 20%
    out["composite"] = (
        0.35 * out["news_z"].clip(-3, 3) +
        0.25 * out["sentiment"].clip(-1, 1) +
        0.20 * (out["market_pct"] / 3.0).clip(-3, 3) +  # scale market %
        0.20 * (out["trends"] / 50.0 - 1.0).clip(-3, 3) # center 50 as baseline
    )

    # tidy
    out = out.sort_values("composite", ascending=False).reset_index(drop=True)
    return out
# ------------------------------
# ANALYTICS: SENTIMENT + BRI
# ------------------------------
import numpy as np
import pandas as pd

# VADER sentiment (robust fallback)
def _ensure_vader():
    try:
        from nltk.sentiment import SentimentIntensityAnalyzer
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        return SentimentIntensityAnalyzer()
    except Exception:
        return None

_VADER = _ensure_vader()

def score_text_sentiment(df: pd.DataFrame, text_col: str = "title") -> pd.DataFrame:
    """
    Adds 'sentiment' (-1..1) from VADER to df. Empty text -> 0.0
    """
    if df is None or df.empty:
        return df
    if text_col not in df.columns:
        df["sentiment"] = 0.0
        return df
    if _VADER is None:
        df["sentiment"] = 0.0
        return df
    def _s(x):
        if not isinstance(x, str) or not x.strip():
            return 0.0
        try:
            return float(_VADER.polarity_scores(x)["compound"])
        except Exception:
            return 0.0
    df = df.copy()
    df["sentiment"] = df[text_col].astype(str).map(_s)
    return df

def robust_zscore(s: pd.Series) -> pd.Series:
    """
    Z via median & IQR; handles constant series and NaNs.
    """
    s = pd.to_numeric(s, errors="coerce")
    med = np.nanmedian(s)
    q1, q3 = np.nanpercentile(s.dropna(), [25, 75]) if s.dropna().size else (np.nan, np.nan)
    iqr = (q3 - q1) if (q3 is not np.nan and q1 is not np.nan) else np.nan
    if np.isnan(iqr) or iqr == 0:
        return pd.Series(np.zeros(len(s)), index=s.index)
    return (s - med) / (iqr / 1.349)

def compute_behavioral_readiness(
    mobility: pd.DataFrame | None,
    trends: pd.DataFrame | None,
    news: pd.DataFrame | None,
    retail_density: pd.DataFrame | None,
    macro: pd.DataFrame | None
) -> pd.DataFrame:
    """
    Returns a tidy frame with Behavioral Readiness Index per (geo or national).
    Columns out: [bucket, metric, value, z, weight, score, bri]
    """
    rows = []

    # Mobility (expect columns: date, value or mobility_index; optional)
    if mobility is not None and not mobility.empty:
        m = mobility.copy()
        col = "value" if "value" in m.columns else ("mobility_index" if "mobility_index" in m.columns else None)
        if col:
            m = m.dropna(subset=[col]).tail(60)
            rows.append(pd.DataFrame({"metric": "mobility", "value": m[col].astype(float).values}))

    # Trends (interest 0..100, average last 14d)
    if trends is not None and not trends.empty:
        t = trends.copy()
        t = t.dropna(subset=["interest"])
        t14 = t[t["date"] >= (pd.Timestamp.utcnow().tz_localize("UTC") - pd.Timedelta(days=14))]
        if not t14.empty:
            rows.append(pd.DataFrame({"metric": "search_intent", "value": [float(t14["interest"].mean())]}))

    # News sentiment (average last 72h)
    if news is not None and not news.empty:
        n = news.copy()
        if "sentiment" in n.columns:
            n72 = n[n["published"] >= (pd.Timestamp.utcnow().tz_localize("UTC") - pd.Timedelta(hours=72))]
            if not n72.empty:
                rows.append(pd.DataFrame({"metric": "sentiment", "value": [float(n72["sentiment"].mean())]}))

    # Retail density (optional; expect numeric 'density')
    if retail_density is not None and not retail_density.empty and "density" in retail_density.columns:
        rd = retail_density.copy()
        rows.append(pd.DataFrame({"metric": "retail_density", "value": [float(rd["density"].mean())]}))

    # Macro (consumer_sentiment scaled)
    if macro is not None and not macro.empty:
        mm = macro.copy()
        # use the latest values
        latest = mm.sort_values("date").groupby("series").tail(1).set_index("series")["value"]
        if "consumer_sentiment" in latest.index:
            rows.append(pd.DataFrame({"metric": "macro_confidence", "value": [float(latest["consumer_sentiment"])]}))

    if not rows:
        return pd.DataFrame(columns=["bucket","metric","value","z","weight","score","bri"])

    allv = pd.concat(rows, ignore_index=True)
    # z-score each metric
    allv["z"] = robust_zscore(allv["value"])

    # weights tuned toward intent & sentiment
    weights = {
        "mobility": 0.30,
        "search_intent": 0.25,
        "sentiment": 0.25,
        "retail_density": 0.15,
        "macro_confidence": 0.05,
    }
    allv["weight"] = allv["metric"].map(weights).fillna(0.0)
    allv["score"] = allv["z"] * allv["weight"]

    bri = float(allv["score"].sum())
    allv["bucket"] = "US-National"
    out = allv.copy()
    out["bri"] = bri
    return out
