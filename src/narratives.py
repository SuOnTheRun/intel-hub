import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

def cluster_topics(df: pd.DataFrame, text_col: str = "text", k: int = 8):
    if df.empty:
        return pd.DataFrame(columns=["cluster","term","weight","sample"])
    texts = df[text_col].fillna("").astype(str).tolist()
    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1,2))
    X = vectorizer.fit_transform(texts)
    k = min(k, max(2, min(10, X.shape[0] // 20)))
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)
    df = df.copy()
    df["cluster"] = labels

    # top terms
    terms = vectorizer.get_feature_names_out()
    centers = model.cluster_centers_
    topic_rows = []
    for i in range(k):
        top_idx = centers[i].argsort()[-8:][::-1]
        for j in top_idx:
            topic_rows.append({"cluster": i, "term": terms[j], "weight": float(centers[i][j])})
    # representative sample per cluster
    samples = df.groupby("cluster")[text_col].apply(lambda s: s.iloc[0] if len(s)>0 else "")
    topic = pd.DataFrame(topic_rows)
    topic["sample"] = topic["cluster"].map(samples.to_dict())
    return topic
