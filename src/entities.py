import spacy
import pandas as pd

_nlp = spacy.load("en_core_web_sm")

def extract_entities_batch(texts):
    if isinstance(texts, pd.Series):
        texts = texts.fillna("").astype(str).tolist()
    ents = []
    for t in texts:
        doc = _nlp(t)
        for e in doc.ents:
            ents.append({"text": t, "entity": e.text, "label": e.label_})
    return pd.DataFrame(ents)
