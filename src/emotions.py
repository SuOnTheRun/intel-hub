# src/emotions.py
import pandas as pd

# --- VADER fallback
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")
_vader = SentimentIntensityAnalyzer()

# --- Transformer (preferred, auto-fallback)
_TRANSFORMER_READY = False
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    _MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    _tok = AutoTokenizer.from_pretrained(_MODEL_NAME, local_files_only=False)
    _mdl = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME, local_files_only=False)
    _mdl.eval()
    _TRANSFORMER_READY = True
except Exception:
    _TRANSFORMER_READY = False

def _sent_transformer(batch_text: list[str]) -> list[float]:
    scores = []
    with torch.no_grad():
        for t in batch_text:
            enc = _tok(t[:512], return_tensors="pt", truncation=True)
            out = _mdl(**enc)
            logits = out.logits[0].detach().cpu().numpy()
            # model labels: ['negative','neutral','positive'] -> compound in [-1,1]
            # softmax -> weighted mapping
            exps = (logits - logits.max()).astype(float)
            exps = (exps ** 1.0)
            probs = (exps / exps.sum())
            compound = probs[2] - probs[0]
            scores.append(float(compound))
    return scores

def _sent_vader(batch_text: list[str]) -> list[float]:
    return [_vader.polarity_scores(t).get("compound", 0.0) for t in batch_text]

def add_sentiment(df: pd.DataFrame, col: str = "title") -> pd.DataFrame:
    if df.empty:
        df["sentiment"] = []
        return df
    texts = df[col].fillna("").astype(str).tolist()
    try:
        if _TRANSFORMER_READY:
            scores = _sent_transformer(texts)
        else:
            scores = _sent_vader(texts)
    except Exception:
        scores = _sent_vader(texts)
    out = df.copy()
    out["sentiment"] = scores
    return out
