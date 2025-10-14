import os, pandas as pd, re
from functools import lru_cache
from pathlib import Path

LEX_URL = "https://raw.githubusercontent.com/words/nrc-emotion-lexicon/master/json/nrc-emotion-lexicon.json"  # open source

@lru_cache(maxsize=1)
def load_lexicon() -> dict:
    # lazy fetch; cached on disk so we don't re-download
    p = Path(".cache_nrc.json")
    if p.exists():
        return pd.read_json(p).to_dict()
    import requests
    r = requests.get(LEX_URL, timeout=20)
    r.raise_for_status()
    data = r.json()
    pd.Series(data).to_json(p)
    return data

def emotion_scores(text: str) -> dict:
    if not text: 
        return {e:0 for e in ("anger","anticipation","disgust","fear","joy","sadness","surprise","trust")}
    lex = load_lexicon()
    toks = re.findall(r"[A-Za-z']+", text.lower())
    scores = {e:0 for e in ("anger","anticipation","disgust","fear","joy","sadness","surprise","trust")}
    for t in toks:
        if t in lex:
            for e,flag in lex[t].items():
                if flag: scores[e] += 1
    total = sum(scores.values()) or 1
    return {k: round(v/total,4) for k,v in scores.items()}
