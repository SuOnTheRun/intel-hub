# src/narratives.py
import pandas as pd
from dataclasses import dataclass

# Preferred: BERTopic
_HAS_BERTOPIC = False
try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    _HAS_BERTOPIC = True
except Exception:
    _HAS_BERTOPIC = False

# Fallback: KeyBERT + MiniLM + KMeans
_HAS_KEYBERT = False
try:
    from keybert import KeyBERT
    from sklearn.cluster import KMeans
    from sentence_transformers import SentenceTransformer
    _HAS_KEYBERT = True
except Exception:
    _HAS_KEYBERT = False

@dataclass
class NarrativeResult:
    table: pd.DataFrame               # columns: [category, narrative, weight, n_docs]
    top_docs_by_cat: dict             # {category: DataFrame[title, link, score]}

def _bertopic_for_cat(df_cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df_cat.empty:
        return pd.DataFrame(columns=["narrative","weight","n_docs"]), df_cat
    docs = (df_cat["title"].fillna("") + ". " + df_cat["summary"].fillna("")).tolist()
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    topic_model = BERTopic(embedding_model=embedder, min_topic_size=4, calculate_probabilities=False, verbose=False)
    topics, _ = topic_model.fit_transform(docs)
    info = topic_model.get_topic_info()
    # Drop outlier = -1
    info = info[info.Topic != -1].copy()
    info["narrative"] = info["Name"].str.replace("_", " ").str.title()
    info["weight"] = info["Count"] / max(1, info["Count"].sum())
    info = info.rename(columns={"Count":"n_docs"})[["narrative","weight","n_docs"]]
    # Top docs per dominant topic
    top_topic = info.sort_values("n_docs", ascending=False).head(1)["narrative"].tolist()
    df_cat = df_cat.copy()
    df_cat["score"] = 1.0  # display only
    return info, df_cat

def _keybert_kmeans_for_cat(df_cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if df_cat.empty:
        return pd.DataFrame(columns=["narrative","weight","n_docs"]), df_cat
    docs = (df_cat["title"].fillna("") + ". " + df_cat["summary"].fillna("")).tolist()
    # Embeddings
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    X = embedder.encode(docs, normalize_embeddings=True, show_progress_bar=False)
    # K auto: clamp between 2 and 6
    k = max(2, min(6, len(docs)//6 or 2))
    km = KMeans(n_clusters=k, n_init="auto", random_state=42)
    labels = km.fit_predict(X)
    df_cat = df_cat.copy()
    df_cat["cluster"] = labels
    # For each cluster, extract keywords via KeyBERT from top doc
    kw_model = KeyBERT(model=embedder)
    rows = []
    for lab, g in df_cat.groupby("cluster"):
        ref = g.iloc[0]
        text = f"{ref['title']}. {ref['summary']}"
        try:
            kws = kw_model.extract_keywords(text, top_n=3, stop_words="english")
            phrase = ", ".join([k for k, _ in kws]) or f"Cluster {lab}"
        except Exception:
            phrase = f"Cluster {lab}"
        rows.append({"narrative": phrase.title(), "weight": len(g)/len(df_cat), "n_docs": len(g)})
    info = pd.DataFrame(rows).sort_values("n_docs", ascending=False)
    df_cat["score"] = 1.0
    return info, df_cat

def build_narratives(news_df: pd.DataFrame, top_n: int = 3) -> NarrativeResult:
    tables = []
    top_docs = {}
    cats = sorted(news_df["category"].dropna().unique().tolist()) if not news_df.empty else []
    for cat in cats:
        g = news_df[news_df["category"] == cat].head(300)  # keep it light
        try:
            if _HAS_BERTOPIC:
                info, docs = _bertopic_for_cat(g)
            elif _HAS_KEYBERT:
                info, docs = _keybert_kmeans_for_cat(g)
            else:
                info, docs = (pd.DataFrame(columns=["narrative","weight","n_docs"]), g)
        except Exception:
            info, docs = (pd.DataFrame(columns=["narrative","weight","n_docs"]), g)
        info["category"] = cat
        tables.append(info.head(top_n))
        top_docs[cat] = g[["title","link","published_dt","source"]].head(8).copy()
    table = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=["category","narrative","weight","n_docs"])
    return NarrativeResult(table=table, top_docs_by_cat=top_docs)
