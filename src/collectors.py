# src/collectors.py  (REPLACE FILE)

import os, re, math
from typing import List, Dict, Any, Optional
import pandas as pd
import feedparser
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pytrends.request import TrendReq

analyzer = SentimentIntensityAnalyzer()

REGIONS = {
    "EU":["DE","FR","IT","ES","NL","SE","PL","IE","AT","BE","DK","FI","PT","GR","CZ","RO","HU"],
    "SEA":["SG","MY","TH","VN","ID","PH"],
    "LATAM":["BR","MX","AR","CL","CO","PE"],
    "MENA":["AE","SA","QA","KW","EG","MA","JO","OM","BH"],
}
TOP_MARKETS = ["US","UK","CA","CN","JP","IN"]

CATEGORIES = {
    "consumer_staples":{"name":"Consumer Staples","keywords":["fmcg","groceries","beverages","household","personal care"],"tickers":["XLP"]},
    "energy":{"name":"Energy","keywords":["oil","gas","petrol","diesel","refinery","renewables","power"],"tickers":["XLE"]},
    "technology":{"name":"Technology","keywords":["ai","semiconductor","chip","software","cloud","datacenter"],"tickers":["XLK"]},
    "automotive":{"name":"Automotive","keywords":["auto","ev","car","cars","battery","dealership"],"tickers":["CARZ"]},
    "financials":{"name":"Financials","keywords":["bank","banking","fintech","credit","payments","lending"],"tickers":["XLF"]},
    "media":{"name":"Media & Advertising","keywords":["advertising","adtech","programmatic","ctv","streaming","social"],"tickers":["XLC"]},
    "healthcare":{"name":"Healthcare","keywords":["pharma","drug","biotech","vaccine","diagnostics","hospital"],"tickers":["XLV"]},
}

NEWS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/worldNews",
]

def _geo_match(text: str, country: Optional[str], region: Optional[str]) -> bool:
    if not country and not region:
        return True
    t = text.lower()
    if country and country.lower() in t: return True
    if region and region.lower() in t: return True
    return False

def _keyword_match(blob: str, kws: List[str]) -> bool:
    b = blob.lower()
    # allow partials and plurals using regex word boundaries where possible
    for k in kws:
        if re.search(rf"\b{k}\b", b): 
            return True
    return False

def fetch_news(category: str, country: Optional[str]=None, region: Optional[str]=None, limit: int=40) -> List[Dict[str,Any]]:
    """Filter Reuters by category keywords + optional geo. Return top-N with VADER on titles."""
    entries = []
    for url in NEWS_FEEDS:
        try:
            entries.extend(feedparser.parse(url).entries)
        except Exception:
            continue
    kws = CATEGORIES[category]["keywords"]
    out = []
    for e in entries:
        title = e.get("title","") or ""
        summary = e.get("summary","") or ""
        blob = f"{title} {summary}"
        if _keyword_match(blob, kws) and _geo_match(blob, country, region):
            score = analyzer.polarity_scores(title)["compound"]
            out.append({
                "title": title,
                "summary": summary,
                "link": e.get("link"),
                "published": e.get("published",""),
                "source": "Reuters",
                "senti": float(score),
            })
        if len(out) >= limit:
            break
    return out

def fetch_quotes(symbols: List[str]) -> List[Dict[str,Any]]:
    out = []
    for s in symbols:
        try:
            hist = yf.Ticker(s).history(period="5d", interval="1d")
            if len(hist) >= 2:
                last = float(hist["Close"].iloc[-1]); prev = float(hist["Close"].iloc[-2])
                chg = last - prev; pct = (chg/prev*100) if prev else 0.0
                out.append({"symbol": s, "last": round(last,2), "change": round(chg,2), "pct": round(pct,2)})
        except Exception:
            continue
    return out

def fetch_trends(category: str, geo: str) -> Dict[str,Any]:
    """Return Google Trends (labels+datasets). If blocked by Google, raise so caller can hide the panel."""
    kw = CATEGORIES[category]["keywords"][:5]
    pt = TrendReq(hl="en-US", tz=0, requests_args={"headers":{"User-Agent":"Mozilla/5.0"}})
    pt.build_payload(kw_list=kw, timeframe="today 3-m", geo=geo)
    df = pt.interest_over_time()
    if df is None or df.empty:
        raise RuntimeError("Empty Trends for scope")
    if "isPartial" in df.columns:
        df = df.drop(columns=["isPartial"])
    labels = [d.strftime("%Y-%m-%d") for d in df.index]
    datasets = [{"label": c, "data": [int(v) if pd.notna(v) else 0 for v in df[c].tolist()]} for c in df.columns]
    return {"labels": labels, "datasets": datasets}

def news_z_dynamic(headlines_now: List[Dict[str,Any]], all_entries_count: int) -> float:
    """
    Data-driven baseline: estimate expected matches from current feed size.
    Baseline = max(3, 0.12 * all_entries_count)  -> ~12% of Reuters items match a sector on average
    """
    N = len(headlines_now)
    baseline = max(3, 0.12 * max(1, all_entries_count))
    std = max(1.0, baseline ** 0.5)
    return (N - baseline) / std

def senti_avg(headlines: List[Dict[str,Any]]) -> float:
    if not headlines:
        return 0.0
    return float(pd.Series([h["senti"] for h in headlines]).mean())

def ccs_simple(news_z_v: float, s_avg: float, trends_delta: float|None, market_norm: float|None) -> float:
    comps = [news_z_v, s_avg]
    if trends_delta is not None: comps.append(trends_delta)
    if market_norm is not None: comps.append(market_norm/50.0)  # soft-normalize market %
    val = sum(comps) / len(comps)
    return max(min(val, 3.0), -3.0)

def estimated_feed_size() -> int:
    """Quick helper so pages can compute a reasonable baseline without a DB."""
    n = 0
    for u in NEWS_FEEDS:
        try: n += len(feedparser.parse(u).entries)
        except Exception: pass
    return n
# --- Backward-compat aliases for existing app.py imports ---
def news_z(headlines):
    from .collectors import news_z_dynamic, estimated_feed_size
    return news_z_dynamic(headlines, estimated_feed_size())

def ccs(news_z_v, s_avg, trends_delta, market_norm):
    from .collectors import ccs_simple
    return ccs_simple(news_z_v, s_avg, trends_delta, market_norm)
