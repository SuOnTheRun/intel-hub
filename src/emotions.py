# src/emotions.py — headline sentiment without NLTK downloads
from __future__ import annotations
import pandas as pd

try:
    # No external downloads required; fast and lightweight
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except Exception:
    SentimentIntensityAnalyzer = None

_analyzer = None

def _get_analyzer():
    global _analyzer
    if _analyzer is None and SentimentIntensityAnalyzer is not None:
        _analyzer = SentimentIntensityAnalyzer()
    return _analyzer

def _score_text(txt: str) -> float:
    a = _get_analyzer()
    if not a or not isinstance(txt, str) or not txt.strip():
        return 0.0
    try:
        return float(a.polarity_scores(txt)["compound"])
    except Exception:
        return 0.0

def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds 'sentiment' column in [-1,+1] using VADER (vaderSentiment package).
    Works on title + summary if both exist.
    """
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    def _row_text(r):
        title = str(r.get("title", "") or "")
        summ  = str(r.get("summary", "") or "")
        return (title + ". " + summ).strip()

    df = df.copy()
    df["sentiment"] = [_score_text(_row_text(r)) for _, r in df.iterrows()]
    return df
