import re
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_an = SentimentIntensityAnalyzer()

# Lightweight region mapping (keyword-based; robust and fast)
_REGION_MAP = {
    "Global": ["global", "world"],
    "Eastern Europe": ["ukraine", "russia", "poland", "belarus", "baltic"],
    "Middle East": ["israel", "gaza", "palestine", "iran", "iraq", "syria", "lebanon", "saudi", "uae", "qatar", "yemen"],
    "Africa": ["nigeria", "kenya", "ethiopia", "south africa", "egypt", "sudan", "libya", "ghana"],
    "South Asia": ["india", "pakistan", "bangladesh", "sri lanka", "nepal"],
    "Indo-Pacific": ["china", "taiwan", "japan", "korea", "australia", "indonesia", "philippines", "vietnam", "malaysia"],
    "Americas": ["united states", "usa", "canada", "mexico", "brazil", "argentina", "colombia", "peru", "chile"],
    "Europe": ["uk", "britain", "france", "germany", "italy", "spain", "european union", "eu"],
}

_TOPIC_MAP = {
    "Markets": ["markets", "stocks", "equity", "bond", "inflation", "tariff", "fed", "rbi", "ecb"],
    "Mobility": ["flight", "airport", "airspace", "air traffic", "ship", "vessel", "rail", "border"],
    "Security": ["attack", "strike", "missile", "bomb", "military", "ceasefire", "sanction"],
    "Elections": ["election", "vote", "polls", "ballot", "campaign"],
    "Technology": ["ai", "chip", "semiconductor", "cloud", "cyber", "data"],
    "Retail": ["retail", "store", "consumer", "footfall", "ecommerce"],
    "Energy": ["oil", "gas", "energy", "coal", "renewable", "solar"],
}

def _classify_region(text: str) -> str:
    t = text.lower()
    for region, keys in _REGION_MAP.items():
        if any(k in t for k in keys):
            return region
    return "Global"

def _classify_topic(text: str) -> str:
    t = text.lower()
    for topic, keys in _TOPIC_MAP.items():
        if any(k in t for k in keys):
            return topic
    return "General"

def _vader_sent(text: str) -> float:
    if not isinstance(text, str):
        return 0.0
    return _an.polarity_scores(text)["compound"]

def enrich_news_with_topics_regions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["source","published_ts","title","link","origin","region","topic","sentiment"])
    d = df.copy()
    d["region"]  = d["title"].fillna("").apply(_classify_region)
    d["topic"]   = d["title"].fillna("").apply(_classify_topic)
    # Deeper sentiment (VADER) complements TextBlob
    d["sentiment"] = d["title"].fillna("").apply(_vader_sent)
    return d

def aggregate_kpis(news_df: pd.DataFrame, gdelt_df: pd.DataFrame, air_df: pd.DataFrame) -> dict:
    total_reports = (0 if news_df is None else len(news_df)) + (0 if gdelt_df is None else len(gdelt_df))
    high_risk_regions = (
        news_df[news_df["topic"].isin(["Security"])].groupby("region").size().shape[0]
        if news_df is not None and not news_df.empty else 0
    )
    aircraft_tracked = 0 if air_df is None else len(air_df)
    movement_detections = (air_df["on_ground"] == False).sum() if air_df is not None and not air_df.empty else 0
    avg_risk = round(max(0, min(10, 5 + (high_risk_regions/4))), 1)  # simple index for display
    return dict(
        total_reports=total_reports,
        movement=movement_detections,
        high_risk_regions=high_risk_regions,
        aircraft=aircraft_tracked,
        avg_risk=avg_risk,
    )

def build_social_listening_panels(news_df: pd.DataFrame, reddit_df: pd.DataFrame):
    blocks = []
    if news_df is not None and not news_df.empty:
        top_regions = news_df.groupby("region").size().sort_values(ascending=False).head(6).index.tolist()
        for r in top_regions:
            subset = news_df[news_df["region"] == r][["published_ts","topic","title","sentiment","source","origin","link"]].head(50)
            blocks.append({"title": f"Region — {r}", "table": subset})
    if reddit_df is not None and not reddit_df.empty:
        rr = reddit_df.sort_values("created_utc", ascending=False).head(100)
        blocks.append({"title": "Reddit — Latest Posts", "table": rr[["created_utc","subreddit","title","score","url","query"]]})
    return blocks
