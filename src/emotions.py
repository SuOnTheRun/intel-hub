import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Ensure lexicon exists on first run (works on Render/Streamlit Cloud)
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

_sia = SentimentIntensityAnalyzer()

def score_sentiment(texts: list[str]) -> list[float]:
    return [_sia.polarity_scores(t).get("compound", 0.0) for t in texts]

def add_sentiment(df: pd.DataFrame, col: str = "title") -> pd.DataFrame:
    if df.empty:
        df["sentiment"] = []
        return df
    df = df.copy()
    df["sentiment"] = score_sentiment(df[col].astype(str).tolist())
    return df
