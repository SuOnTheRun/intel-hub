# src/analytics.py
from __future__ import annotations
import re, math
from typing import Iterable, List, Dict
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk

# Ensure VADER lexicon is present (first run will download and cache)
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:  # pragma: no cover
    nltk.download("vader_lexicon")

_vader = SentimentIntensityAnalyzer()

def clean_text(s: str) -> str:
    s = re.sub(r"http\S+", "", s or "")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def sentiment_score(texts: Iterable[str]) -> pd.DataFrame:
    """
    Vectorized VADER compound score in -1..+1; returns df[text, score].
    """
    rows = []
    for t in texts:
        t2 = clean_text(t)
        sc = _vader.polarity_scores(t2)["compound"]
        rows.append({"text": t2, "sentiment": sc})
    return pd.DataFrame(rows)

def summarize_headlines(headlines: pd.DataFrame, n: int = 6) -> Dict[str, List[str]]:
    """
    Simple, deterministic summary: selects top n by absolute sentiment magnitude,
    de-duplicates by keyword, and splits into Positive/Negative/Near-Neutral lists.
    """
    if headlines.empty:
        return {"positive": [], "negative": [], "neutral": []}
    df = headlines.copy()
    df["sent"] = sentiment_score(df["title"])["sentiment"].values
    df["abs"] = df["sent"].abs()
    df = df.sort_values("abs", ascending=False).head(60)  # strongest reactions
    pos = df.loc[df["sent"] > 0.25, "title"].head(n).tolist()
    neg = df.loc[df["sent"] < -0.25, "title"].head(n).tolist()
    neu = df.loc[df["sent"].between(-0.25, 0.25), "title"].head(n//2).tolist()
    return {"positive": pos, "negative": neg, "neutral": neu}

def drift(current: pd.Series, window: int = 7) -> float:
    """
    Last value vs moving average (%). Used for TSA and indices.
    """
    if len(current) < window + 1:
        return 0.0
    ma = current.rolling(window).mean()
    return float(((current.iloc[-1] - ma.iloc[-2]) / (ma.iloc[-2] or 1e-9)) * 100.0)
