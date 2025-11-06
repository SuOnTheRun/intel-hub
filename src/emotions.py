import os
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import pandas as pd

# Ensure VADER is available at runtime
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

_sia = SentimentIntensityAnalyzer()

def score_sentiment_batch(texts):
    if isinstance(texts, pd.Series):
        texts = texts.fillna("").astype(str).tolist()
    out = [_sia.polarity_scores(t) for t in texts]
    return pd.DataFrame(out)
