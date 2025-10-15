# src/narratives.py
import pandas as pd
from dataclasses import dataclass

# Flags for optional heavy libs (will be False on free plan)
_HAS_BERTOPIC = False
try:
    from bertopic import BERTopic
    from sentence_transformers import SentenceTransformer
    _HAS_BERTOPIC = True
except Exception:
    _HAS_BERTOPIC = False

_HAS_KEYBERT = False
try:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer
    from sklearn.cluster import KMeans
    _HAS_KEYBERT = True
except Exception:
    _HAS_KEYBERT = False

# Pure sklearn fallback (works with scikit-learn only)
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

@dataclass
class NarrativeResult:
    table: pd.DataFrame               # [category, narrative, weight, n_docs]
    top_docs_by_cat: dict             # {category: DataFrame[title, link, published_dt, source]}

def _bertopic_for_cat(df_cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    docs = (df_cat["title"].fillna("") + ". " + df_cat["summary"].fillna("")).tolist()
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    topic_model = BERTopic(embedding_model=embedder, min_topic_size=4, calculate_probabilities=False, verbose=False)
    topics, _ = topic_model.fit_transform(docs)
    info = topic_model.get_topic_info()
    info = info[info.Topic != -1].copy()
    info["narrative"] = info["Name"].str.replace("_", " ").str.title()
    info["weight"] = info["Count"] / max(1, info["Count"].sum())
    info = info.rename(columns={"Count":"n_docs"})[["narrative","weight","n_docs"]]
    df_cat = df_cat.copy()
    df_cat["score"] = 1.0
    return info, df_cat

def _keybert_kmeans_for_cat(df_cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    kw_model = KeyBERT(model=embedder)
    texts = (df_cat["title"].fillna("") + ". " + df_cat["summary"].fillna("")).tolist()
    # lightweight clustering over TF-IDF
    vect = TfidfVectorizer(max_features=4000, ngram_range=(1,2), stop_words="english")
    X = vect.fit_transform(texts)
    k = max(2, min(6, X.shape[0] // 6 or 2))
    labels = KMeans(n_clusters=k, n_init="auto", random_state=42).fit_predict(X)
    df_cat = df_cat.copy()
    df_cat["cluster"] = labels
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

def _tfidf_kmeans_fallback(df_cat: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Zero-heavy fallback: TF-IDF + KMeans, no transformers/keybert/bertopic."""
    texts = (df_cat["title"].fillna("") + ". " + df_cat["summary"].fillna("")).tolist()
    if not texts:
        return pd.DataFrame(columns=["narrative","weight","n_docs"]), df_cat
    vect = TfidfVectorizer(max_features=4000, ngram_range=(1,2), stop_words="english")
    X = vect.fit_transform(texts)
    k = max(2, min(6, X.shape[0] // 6 or 2))
    km = KMeans(n_clusters=k, n_init="auto", random_state=42).fit(X)
    labels = km.labels_
    df_cat = df_cat.copy()
    df_cat["cluster"] = labels
    # label clusters by top TF-IDF n-grams
    terms = vect.get_feature_names_out()
    centers = km.cluster_centers_.toarray() if hasattr(km.cluster_centers_, "toarray") else km.cluster_centers_
    names = []
    for i in range(k):
        top_idx = centers[i].argsort()[-3:][::-1]
        phrase = ", ".join([terms[j] for j in top_idx])
        names.append(phrase.title() if phrase else f"Cluster {i}")
    rows = []
    for i, g in df_cat.groupby("cluster"):
        rows.append({"narrative": names[i], "weight": len(g)/len(df_cat), "n_docs": len(g)})
    info = pd.DataFrame(rows).sort_values("n_docs", ascending=False)
    df_cat["score"] = 1.0
    return info, df_cat

@dataclass
class NarrativeResult:
    table: pd.DataFrame
    top_docs_by_cat: dict

def build_narratives(news_df: pd.DataFrame, top_n: int = 3) -> NarrativeResult:
    tables = []
    top_docs = {}
    cats = sorted(news_df["category"].dropna().unique().tolist()) if not news_df.empty else []
    for cat in cats:
        g = news_df[news_df["category"] == cat].head(300)
        try:
            if _HAS_BERTOPIC:
                info, docs = _bertopic_for_cat(g)
            elif _HAS_KEYBERT:
                info, docs = _keybert_kmeans_for_cat(g)
            else:
                info, docs = _tfidf_kmeans_fallback(g)
        except Exception:
            info, docs = _tfidf_kmeans_fallback(g)
        info["category"] = cat
        tables.append(info.head(top_n))
        top_docs[cat] = g[["title","link","published_dt","source"]].head(8).copy()
    table = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame(columns=["category","narrative","weight","n_docs"])
    return NarrativeResult(table=table, top_docs_by_cat=top_docs)
