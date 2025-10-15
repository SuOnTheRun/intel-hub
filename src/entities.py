# src/entities.py
import pandas as pd

_NLP = None

def _ensure_nlp():
    """
    Try to load spaCy small English model. If anything fails, return None (we'll
    fall back to a simple capitalized-word heuristic). Never raise here.
    """
    global _NLP
    if _NLP is not None:
        return _NLP
    try:
        import spacy  # may not exist on free plan
        try:
            _NLP = spacy.load("en_core_web_sm")
        except Exception:
            # Model not present; don’t attempt download on free hosts
            _NLP = None
    except Exception:
        _NLP = None
    return _NLP

WHITELIST = {"ORG", "PERSON", "GPE"}

def extract_entities(news_df: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """
    Returns DataFrame columns: [category, label, entity, count]
    """
    if news_df.empty:
        return pd.DataFrame(columns=["category","label","entity","count"])

    nlp = _ensure_nlp()
    rows = []

    for cat, g in news_df.groupby("category"):
        texts = (g["title"].fillna("") + ". " + g["summary"].fillna("")).tolist()[:200]

        if nlp is None:
            # Heuristic fallback: count capitalized tokens (quick & robust)
            counts = {}
            for t in texts:
                for w in t.split():
                    w = w.strip(",.;:()[]{}'\"")
                    if w.istitle() and len(w) > 3:
                        key = (cat, "ORG", w)
                        counts[key] = counts.get(key, 0) + 1
            items = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
            for (c,lbl,ent),cnt in items:
                rows.append({"category": c, "label": lbl, "entity": ent, "count": cnt})
            continue

        # spaCy path
        counts = {}
        for d in nlp.pipe(texts, batch_size=32, disable=["tagger","lemmatizer","textcat"]):
            for ent in d.ents:
                if ent.label_ in WHITELIST:
                    key = (cat, ent.label_, ent.text.strip())
                    counts[key] = counts.get(key, 0) + 1
        items = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
        for (c,lbl,ent),cnt in items:
            rows.append({"category": c, "label": lbl, "entity": ent, "count": cnt})

    return pd.DataFrame(rows)
