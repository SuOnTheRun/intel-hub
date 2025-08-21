import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from .presets import REGION_PRESETS, region_keywords

_an = SentimentIntensityAnalyzer()

TOPIC_MAP = {
    "Security":  ["attack","strike","missile","drone","shelling","ceasefire","sanction","mobilization","military","naval","army"],
    "Mobility":  ["flight","airport","airspace","rail","border","vessel","ship","tanker","port","blockade"],
    "Markets":   ["markets","stocks","equity","bond","tariff","inflation","currency","oil","gas","commodity"],
    "Elections": ["election","vote","ballot","poll","campaign","parliament"],
    "Technology":["ai","semiconductor","chip","cyber","data","cloud","satellite"],
    "Retail":    ["retail","consumer","footfall","ecommerce","store"],
    "Energy":    ["pipeline","refinery","power","grid","nuclear","renewable","solar","coal"],
}
TOPIC_LIST = list(TOPIC_MAP.keys())

SOURCE_WEIGHTS = {
    "reuters": 1.25, "bbc": 1.2, "associated press": 1.2, "ap": 1.2,
    "al jazeera": 1.1, "financial times": 1.15, "bloomberg": 1.15, "nytimes": 1.15
}
TOPIC_WEIGHTS = {"Security":1.5,"Mobility":1.25,"Elections":1.2,"Markets":1.15,"Energy":1.15,"Technology":1.1,"Retail":1.05}

def _classify_topic(text: str) -> str:
    t = (text or "").lower()
    for topic, keys in TOPIC_MAP.items():
        if any(k in t for k in keys):
            return topic
    return "General"

def _classify_region(text: str) -> str:
    t = (text or "").lower()
    for region, preset in REGION_PRESETS.items():
        keys = preset.get("keywords", [])
        if any(k in t for k in keys):
            return region
    # fallback buckets
    return "Global"

def _vader_sent(text: str) -> float:
    if not isinstance(text, str): return 0.0
    return _an.polarity_scores(text)["compound"]

def enrich_news_with_topics_regions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["source","published_ts","title","link","origin","region","topic","sentiment"])
    d = df.copy()
    d["region"] = d["title"].fillna("").apply(_classify_region)
    d["topic"]  = d["title"].fillna("").apply(_classify_topic)
    d["sentiment"] = d["title"].fillna("").apply(_vader_sent)
    return d

def _risk_row(row) -> float:
    # Recency (hours)
    recency_h = 12.0
    try:
        now_utc = pd.Timestamp.now(tz="UTC")  # ✅ tz-aware safely
        recency_h = max(0.25, (now_utc - row["published_ts"]).total_seconds() / 3600.0)
    except Exception:
        pass
    # Topic
    tw = TOPIC_WEIGHTS.get(row.get("topic",""), 1.0)
    # Source
    sw = 1.0
    s = (row.get("source") or "").lower()
    for k, v in SOURCE_WEIGHTS.items():
        if k in s:
            sw = v
            break
    # Sentiment (more negative ⇒ higher)
    sent = row.get("sentiment", 0.0)
    sf = 1.0 + max(0.0, -sent)
    score = 100 * tw * sw * sf / (1 + 0.15 * recency_h)
    return round(score, 1)

def add_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    d = df.copy()
    d["risk"] = d.apply(_risk_row, axis=1)
    return d

def filter_by_controls(df: pd.DataFrame, region: str, topics: list, hours: int) -> pd.DataFrame:
    if df is None or df.empty: 
        return df
    d = df.copy()
    if region and region != "Global":
        d = d[d["region"] == region]
        if len(d) < 10:
            keys = region_keywords(region)
            d = df[df["title"].str.lower().str.contains("|".join(keys), na=False)]
    if topics:
        d = d[d["topic"].isin(topics)]
    if hours and "published_ts" in d.columns:
        # ✅ get an already tz-aware UTC “now”
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
        d = d[d["published_ts"] >= cutoff]
    return d


def aggregate_kpis(news_df: pd.DataFrame, gdelt_df: pd.DataFrame, air_df: pd.DataFrame) -> dict:
    total_reports = (0 if news_df is None else len(news_df)) + (0 if gdelt_df is None else len(gdelt_df))
    high_risk_regions = (news_df[news_df["topic"].isin(["Security"])].groupby("region").size().shape[0]
                         if news_df is not None and not news_df.empty else 0)
    aircraft_tracked = 0 if air_df is None else len(air_df)
    movement_detections = (air_df["on_ground"] == False).sum() if air_df is not None and not air_df.empty else 0
    avg_risk = round(max(0, min(10, 5 + (high_risk_regions/4))), 1)
    return dict(total_reports=total_reports, movement=movement_detections, high_risk_regions=high_risk_regions,
                aircraft=aircraft_tracked, avg_risk=avg_risk)

def build_social_listening_panels(news_df: pd.DataFrame, reddit_df: pd.DataFrame):
    blocks = []
    if news_df is not None and not news_df.empty:
        top_regions = news_df.groupby("region").size().sort_values(ascending=False).head(6).index.tolist()
        for r in top_regions:
            subset = news_df[news_df["region"] == r][["published_ts","topic","title","risk","sentiment","source","origin","link"]].head(50)
            blocks.append({"title": f"Region — {r}", "table": subset})
    if reddit_df is not None and not reddit_df.empty:
        rr = reddit_df.sort_values("created_utc", ascending=False).head(100)
        blocks.append({"title": "Reddit — Latest Posts", "table": rr[["created_utc","subreddit","title","score","url","query"]]})
    return blocks
