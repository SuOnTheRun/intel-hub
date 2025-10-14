import os, math, re
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
import feedparser
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pytrends.request import TrendReq

analyzer = SentimentIntensityAnalyzer()

REGIONS = {
    "EU":  ["DE","FR","IT","ES","NL","SE","PL","IE","AT","BE","DK","FI","PT","GR","CZ","RO","HU"],
    "SEA": ["SG","MY","TH","VN","ID","PH"],
    "LATAM":["BR","MX","AR","CL","CO","PE"],
    "MENA":["AE","SA","QA","KW","EG","MA","JO","OM","BH"]
}
TOP_MARKETS = ["US","UK","CA","CN","JP","IN"]

CATEGORIES = {
    "consumer_staples": {"name":"Consumer Staples","keywords":["FMCG","groceries","beverages","personal care"],"tickers":["XLP"]},
    "energy": {"name":"Energy","keywords":["oil","gas","renewables","power"],"tickers":["XLE"]},
    "technology": {"name":"Technology","keywords":["AI","semiconductor","software","cloud"],"tickers":["XLK"]},
    "automotive": {"name":"Automotive","keywords":["EV","cars","battery","dealership"],"tickers":["CARZ"]},
    "financials": {"name":"Financials","keywords":["banking","fintech","credit","payments"],"tickers":["XLF"]},
    "media": {"name":"Media & Advertising","keywords":["advertising","CTV","social","streaming"],"tickers":["XLC"]},
    "healthcare": {"name":"Healthcare","keywords":["pharma","biotech","vaccine","diagnostics"],"tickers":["XLV"]},
}

NEWS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/worldNews",
]

def _geo_match(text: str, country: Optional[str], region: Optional[str]) -> bool:
    if not country and not region: return True
    t = text.lower()
    if country and country.lower() in t: return True
    if region and region.lower() in t: return True
    return False

def fetch_news(category: str, country: Optional[str]=None, region: Optional[str]=None, limit: int=45):
    entries = []
    for url in NEWS_FEEDS:
        try: entries.extend(feedparser.parse(url).entries)
        except Exception: continue
    kws = [k.lower() for k in CATEGORIES[category]["keywords"]]
    out = []
    for e in entries:
        title = e.get("title",""); summary = e.get("summary","")
        blob = f"{title} {summary}".lower()
        if any(k in blob for k in kws) and _geo_match(blob, country, region):
            s = analyzer.polarity_scores(title)["compound"]
            out.append({"title": e.get("title",""), "summary": summary, "link": e.get("link"),
                        "published": e.get("published",""), "source": "Reuters", "senti": s})
        if len(out) >= limit: break
    return out

def fetch_quotes(symbols: List[str]):
    out = []
    for s in symbols:
        try:
            hist = yf.Ticker(s).history(period="5d", interval="1d")
            if len(hist) >= 2:
                last = float(hist["Close"].iloc[-1]); prev = float(hist["Close"].iloc[-2])
                chg = last - prev; pct = (chg/prev*100) if prev else 0.0
                out.append({"symbol": s, "last": round(last,2), "change": round(chg,2), "pct": round(pct,2)})
        except Exception: continue
    return out

def fetch_trends(category: str, geo: str):
    kw = CATEGORIES[category]["keywords"][:5]
    pytrend = TrendReq(hl="en-US", tz=330)
    pytrend.build_payload(kw_list=kw, timeframe="today 3-m", geo=geo)
    df = pytrend.interest_over_time()
    if "isPartial" in df.columns: df = df.drop(columns=["isPartial"])
    labels = [d.strftime("%Y-%m-%d") for d in df.index]
    datasets = [{"label": c, "data": [int(v) if pd.notna(v) else 0 for v in df[c].tolist()]} for c in df.columns]
    return {"labels": labels, "datasets": datasets}

def news_z(headlines: list, baseline: int=60) -> float:
    N = len(headlines); mean = baseline; std = max(1, baseline**0.5)
    return (N - mean) / std

def senti_avg(headlines: list) -> float:
    if not headlines: return 0.0
    return float(pd.Series([h["senti"] for h in headlines]).mean())

def ccs(news_z_v: float, s_avg: float, trends_delta: float, market_norm: float) -> float:
    # simple equal-weight composite; clamp to [-3, +3]
    val = (news_z_v + s_avg + trends_delta + market_norm) / 4.0
    return max(min(val, 3.0), -3.0)
