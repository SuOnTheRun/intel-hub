import pandas as pd
import numpy as np

def aggregate_category_metrics(news: pd.DataFrame, social: pd.DataFrame, trends: pd.DataFrame, stocks: pd.DataFrame):
    out = []
    for cat in ["Macro","Technology","Consumer","Energy","Healthcare","Finance","Retail","Autos"]:
        n = len(news[news["title"].str.contains(cat, case=False, na=False)])
        s = len(social[social["title"].str.contains(cat, case=False, na=False)])
        t = trends["category"].astype(str).str.contains(cat, case=False, na=False).sum() if "category" in trends else 0
        out.append({"category": cat, "news_items": int(n), "social_items": int(s), "trend_points": int(t)})
    return pd.DataFrame(out)

def build_kpi_cards(df: pd.DataFrame):
    # placeholder utility; Cards are rendered in UI file
    return df
