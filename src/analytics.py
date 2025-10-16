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
