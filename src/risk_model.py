import numpy as np
import pandas as pd

def compute_risk_index(news: pd.DataFrame, social: pd.DataFrame, trends: pd.DataFrame, stocks: pd.DataFrame):
    # Simple composite: negative share + volatility proxy + trend momentum + market drawdown intraday
    def neg_share(d):
        if d.empty or "sentiment" not in d:
            return 0.0
        return float((d["sentiment"] < -0.05).mean())
    def market_drawdown(s):
        if s.empty:
            return 0.0
        return float((-s["pct"].clip(lower=-10, upper=0).mean())/10.0)

    idx = {}
    for cat in ["Macro","Technology","Consumer","Energy","Healthcare","Finance","Retail","Autos"]:
        n = news[news["title"].str.contains(cat, case=False, na=False)]
        s = social[social["title"].str.contains(cat, case=False, na=False)]
        score = 40*neg_share(n) + 30*neg_share(s) + 30*market_drawdown(stocks)
        idx[cat] = round(max(0,min(100, score*100)), 1) if score <= 1 else 100.0
    return pd.DataFrame({"category": list(idx.keys()), "tension_index": list(idx.values())})
