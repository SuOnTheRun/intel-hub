# src/sentiment_model.py
from __future__ import annotations
import pandas as pd
import numpy as np
from textblob import TextBlob

def compute_sentiment(df: pd.DataFrame, text_col: str = "title"):
    """Very light sentiment estimator using TextBlob polarity."""
    if df is None or df.empty or text_col not in df.columns:
        return {"avg": np.nan, "hist": pd.DataFrame()}
    out = []
    for _, r in df.iterrows():
        text = str(r.get(text_col, ""))
        if not text.strip():
            continue
        pol = TextBlob(text).sentiment.polarity
        out.append(pol)
    if not out:
        return {"avg": np.nan, "hist": pd.DataFrame()}
    scores = pd.Series(out)
    return {"avg": scores.mean(), "hist": scores}

def sentiment_change(current_df: pd.DataFrame, prev_df: pd.DataFrame):
    """Compare average polarity between two frames."""
    cur = compute_sentiment(current_df)["avg"]
    prev = compute_sentiment(prev_df)["avg"]
    if np.isnan(cur) or np.isnan(prev):
        return np.nan
    return cur - prev
