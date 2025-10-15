# src/risk_model.py
import pandas as pd
import numpy as np

def _minmax(s: pd.Series) -> pd.Series:
    if s.max() == s.min():
        return pd.Series([0.0]*len(s), index=s.index)
    return (s - s.min()) / (s.max() - s.min())

def compute_tension(news_df: pd.DataFrame, heat_df: pd.DataFrame, entities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns DataFrame:
      [category, tension_0_100, drivers_json, neg_density, sent_vol, news_z, market_drawdown, trends_norm, entity_intensity]
    where drivers_json is a small dict of standardized inputs for transparency.
    """
    if heat_df.empty:
        return pd.DataFrame(columns=["category","tension_0_100","drivers_json"])

    # Base signals from heat_df
    base = heat_df[["category","news_z","sentiment","market_pct","trends"]].copy()
    base["market_drawdown"] = (-base["market_pct"]).clip(lower=0)  # only penalize drawdown

    # Sentiment density & volatility from news_df
    sent_stats = news_df.groupby("category")["sentiment"].agg(
        neg_density=lambda s: (s < -0.2).mean(),
        sent_vol=lambda s: s.std(ddof=0)
    ).reset_index() if not news_df.empty else pd.DataFrame(columns=["category","neg_density","sent_vol"])

    # Entity intensity from entities_df
    ent = entities_df.groupby("category")["count"].sum().rename("entity_hits").reset_index() if not entities_df.empty else pd.DataFrame(columns=["category","entity_hits"])

    df = base.merge(sent_stats, on="category", how="left").merge(ent, on="category", how="left")
    for c in ["neg_density","sent_vol","entity_hits"]:
        df[c] = df[c].fillna(0.0)

    # Normalize relevant features
    news_norm = _minmax(df["news_z"].clip(lower=0))          # only upside in volume is "risk attention"
    neg_norm = _minmax(df["neg_density"])
    vol_norm = _minmax(df["sent_vol"])
    mdd_norm = _minmax(df["market_drawdown"])
    trd_norm = _minmax(df["trends"])
    ent_norm = _minmax(df["entity_hits"])

    # Weighted blend (tuneable)
    # Heavier weight to negative density and drawdown; then volatility and news; then trends & entities
    tension = (
        0.25 * neg_norm +
        0.20 * mdd_norm +
        0.20 * vol_norm +
        0.15 * news_norm +
        0.10 * trd_norm +
        0.10 * ent_norm
    )

    out = df[["category"]].copy()
    out["tension_0_100"] = (tension * 100).round(1)
    out["neg_density"] = (neg_norm * 100).round(1)
    out["sent_vol"] = (vol_norm * 100).round(1)
    out["news_z"] = df["news_z"].round(2)
    out["market_drawdown"] = df["market_drawdown"].round(2)
    out["trends_norm"] = (trd_norm * 100).round(1)
    out["entity_intensity"] = (ent_norm * 100).round(1)
    # driver bundle for transparency
    out["drivers_json"] = (
        "{"
        + "neg_density:" + out["neg_density"].astype(str) + ", "
        + "sent_vol:" + out["sent_vol"].astype(str) + ", "
        + "news_z:" + out["news_z"].astype(str) + ", "
        + "mkt_dd:" + out["market_drawdown"].astype(str) + ", "
        + "trends:" + out["trends_norm"].astype(str) + ", "
        + "entity:" + out["entity_intensity"].astype(str)
        + "}"
    )
    return out.sort_values("tension_0_100", ascending=False).reset_index(drop=True)
