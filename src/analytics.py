import pandas as pd, numpy as np

def zscore(s: pd.Series) -> pd.Series:
    if s.std(ddof=0) == 0:
        return pd.Series([0]*len(s), index=s.index)
    return (s - s.mean()) / s.std(ddof=0)

def build_category_heatmap(news_df: pd.DataFrame, base_df: pd.DataFrame) -> pd.DataFrame:
    # news volume per category
    if news_df.empty:
        base_df = base_df.copy()
        base_df["news_count"] = 0
    else:
        counts = news_df.groupby("category").size().rename("news_count")
        base_df = base_df.merge(counts, on="category", how="left").fillna({"news_count":0})

    # sentiment per category
    if not news_df.empty and "sentiment" in news_df.columns:
        senti = news_df.groupby("category")["sentiment"].mean().rename("sentiment")
        base_df = base_df.merge(senti, on="category", how="left")
    else:
        base_df["sentiment"] = 0.0

    base_df["news_z"] = zscore(base_df["news_count"])
    base_df["market_z"] = zscore(base_df["market_pct"])
    base_df["composite"] = base_df[["news_z","market_z","sentiment"]].mean(axis=1)
    ordered = base_df[["category","news_z","sentiment","market_pct","composite","news_count","trends"]].sort_values("composite", ascending=False)
    return ordered.reset_index(drop=True)

def headline_blocks(news_df: pd.DataFrame, by_category=True, top_n=6):
    if news_df.empty:
        return { }
    if by_category:
        out = {}
        for cat, g in news_df.groupby("category"):
            out[cat] = g.sort_values("published_dt", ascending=False).head(top_n)
        return out
    else:
        return {"All": news_df.sort_values("published_dt", ascending=False).head(top_n)}
