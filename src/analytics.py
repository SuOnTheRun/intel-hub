import pandas as pd
from .data_sources import category_market_trends

CATS = [
    "Macro","Technology","Consumer","Energy","Healthcare",
    "Finance","Retail","Autos"
]

def aggregate_category_metrics(news: pd.DataFrame, social: pd.DataFrame, trends: pd.DataFrame, stocks: pd.DataFrame):
    """
    Lightweight coverage counters used on the Command Center.
    """
    out = []
    for cat in CATS:
        n = len(news[news["title"].str.contains(cat, case=False, na=False)])
        s = len(social[social["title"].str.contains(cat, case=False, na=False)])
        t = trends.shape[0]
        out.append({"category": cat, "news_items": int(n), "social_items": int(s), "trend_points": int(t)})
    return pd.DataFrame(out)

def build_kpi_cards(df: pd.DataFrame):
    return df

def category_market_trends_table(lookback_days: int = 7) -> pd.DataFrame:
    """
    Pulls the robust category market/trend signals from data_sources.
    """
    return category_market_trends(lookback_days=lookback_days, geo="US")
