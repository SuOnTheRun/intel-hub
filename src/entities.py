# src/entities.py
import pandas as pd

_NLP = None
def _ensure_nlp():
    global _NLP
    if _NLP is not None:
        return _NLP
    import spacy
    try:
        _NLP = spacy.load("en_core_web_sm")
    except Exception:
        try:
            from spacy.cli import download
            download("en_core_web_sm")
            _NLP = spacy.load("en_core_web_sm")
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
            # graceful: fallback by capitalized token heuristic
            counts = {}
            for t in texts:
                for w in t.split():
                    if w.istitle() and len(w) > 3:
                        counts[(cat,"ORG",w)] = counts.get((cat,"ORG",w), 0) + 1
            items = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
            for (c,lbl,ent),cnt in items:
                rows.append({"category": c, "label": lbl, "entity": ent, "count": cnt})
            continue
        doc = nlp.pipe(texts, batch_size=32, disable=["tagger","lemmatizer","textcat"])
        counts = {}
        for d in doc:
            for ent in d.ents:
                if ent.label_ in WHITELIST:
                    key = (cat, ent.label_, ent.text.strip())
                    counts[key] = counts.get(key, 0) + 1
        items = sorted(counts.items(), key=lambda x: -x[1])[:top_n]
        for (c,lbl,ent),cnt in items:
            rows.append({"category": c, "label": lbl, "entity": ent, "count": cnt})
    return pd.DataFrame(rows)
