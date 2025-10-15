import re, math, requests, feedparser, yfinance as yf
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from dateutil import parser as dtparse
from .secrets import NEWSAPI_KEY, REDDIT, POLYGON_KEY
from .emotions import emotion_scores

analyzer = SentimentIntensityAnalyzer()

# ----- Geo & categories -----
REGIONS = {
    "EU":["DE","FR","IT","ES","NL","SE","PL","IE","AT","BE","DK","FI","PT","GR","CZ","RO","HU"],
    "SEA":["SG","MY","TH","VN","ID","PH"],
    "LATAM":["BR","MX","AR","CL","CO","PE"],
    "MENA":["AE","SA","QA","KW","EG","MA","JO","OM","BH"],
}
TOP_MARKETS = ["US","UK","CA","CN","JP","IN"]

CATEGORIES = {
    "consumer_staples":{"name":"Consumer Staples","keywords":["grocery","supermarket","beverages","household","personal care","retail"],"tickers":["XLP"]},
    "energy":{"name":"Energy","keywords":["oil","gas","refinery","opec","renewables","power","utilities"],"tickers":["XLE"]},
    "technology":{"name":"Technology","keywords":["ai","chip","semiconductor","software","cloud","datacenter","smartphone"],"tickers":["XLK"]},
    "automotive":{"name":"Automotive","keywords":["auto","ev","car","cars","battery","supplier","dealership","charging"],"tickers":["CARZ"]},
    "financials":{"name":"Financials","keywords":["bank","fintech","credit","payments","lending","mortgage"],"tickers":["XLF"]},
    "media":{"name":"Media & Advertising","keywords":["advertising","adtech","programmatic","ctv","streaming","social","attention"],"tickers":["XLC"]},
    "healthcare":{"name":"Healthcare","keywords":["pharma","drug","biotech","vaccine","diagnostics","hospital"],"tickers":["XLV"]},
}

# Risk/opportunity lexicons (very light, transparent)
RISK_TERMS  = ["recall","regulator","fine","lawsuit","ban","shortage","strike","layoff","guidance cut","warning","breach","outage"]
OPP_TERMS   = ["upgrade","beat estimates","surge","launch","expansion","partnership","approval","record","growth"]

# BBC / Al Jazeera / AP / DW / CNBC / FT / Reuters / Guardian / CNN
RSS_FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://apnews.com/hub/apf-topnews?utm_source=rss",
    "https://apnews.com/hub/apf-business?utm_source=rss",
    "https://rss.dw.com/rdf/rss-en-ger",
    "https://rss.dw.com/rdf/rss-en-top",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "https://www.cnbc.com/id/10000108/device/rss/rss.html",
    "https://www.ft.com/rss/home/uk",
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/worldNews",
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/business/rss",
    "http://rss.cnn.com/rss/money_latest.rss",
]

SOURCE_WEIGHT = {
    "reuters.com":1.0, "ft.com":0.9, "bbc.co.uk":0.9, "aljazeera.com":0.85, "apnews.com":0.9,
    "dw.com":0.75, "cnbc.com":0.8, "theguardian.com":0.75, "cnn.com":0.6
}

def _src_from_url(url: str) -> str:
    m = re.match(r"https?://(www\.)?([^/]+)/?", url or "")
    return (m.group(2) if m else "source").lower()

def _geo_match(text: str, country: Optional[str], region: Optional[str]) -> float:
    """Return geo bonus (0 or >0)."""
    t = (text or "").lower()
    bonus = 0.0
    if country and country.lower() in t: bonus += 0.8
    if region and region.lower() in t: bonus += 0.4
    return bonus

def _keyword_hits(text: str, kws: List[str]) -> int:
    b = (text or "").lower()
    return sum(1 for k in kws if re.search(rf"\b{k}\b", b))

def _score_item(title: str, summary: str, src_host: str, kws: List[str], country: Optional[str], region: Optional[str]) -> Tuple[float, dict]:
    blob = f"{title} {summary}".lower()
    kw = _keyword_hits(blob, kws)                               # relevance to category
    geo = _geo_match(blob, country, region)                     # relevance to geo
    sw = SOURCE_WEIGHT.get(src_host, 0.5)                       # source trust weight
    senti = analyzer.polarity_scores(title)["compound"]
    emo = emotion_scores(f"{title}. {summary}")
    risk = int(any(term in blob for term in RISK_TERMS))
    opp  = int(any(term in blob for term in OPP_TERMS))
    # BM25-like light score
    score = kw*1.2 + geo + sw*0.6 + (abs(senti)*0.1) + opp*0.2 - risk*0.1
    meta = {"senti": float(senti), "emotions": emo, "risk": risk, "opportunity": opp}
    return score, meta

def _parse_dt(s: str) -> pd.Timestamp:
    try:
        return pd.Timestamp(dtparse.parse(s))
    except Exception:
        return pd.Timestamp.utcnow()

def _dedupe(items: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    seen=set(); out=[]
    for it in items:
        key = it["title"].strip().lower()
        if key in seen: continue
        seen.add(key); out.append(it)
    return out

def fetch_news_rss(category: str, country: Optional[str], region: Optional[str], limit: int=120) -> List[Dict[str,Any]]:
    kws = CATEGORIES[category]["keywords"]; candidates=[]
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:70]:
                title = e.get("title","") or ""; summary = e.get("summary","") or ""
                link = e.get("link"); pub = e.get("published","")
                src_host = _src_from_url(url)
                score, meta = _score_item(title, summary, src_host, kws, country, region)
                # keep everything; sort by score later (no fake filtering)
                candidates.append({
                    "title": title, "summary": summary, "link": link, "published": pub,
                    "source": src_host, "score": score, **meta
                })
        except Exception:
            continue
    # sort by relevance score & recency
    for it in candidates:
        it["_ts"] = _parse_dt(it["published"])
    ranked = sorted(candidates, key=lambda x:(x["score"], x["_ts"]), reverse=True)
    ranked = _dedupe(ranked)
    return ranked[:limit]

def fetch_news_newsapi(category: str, country: Optional[str], region: Optional[str], limit:int=100) -> List[Dict[str,Any]]:
    if not NEWSAPI_KEY:
        return []
    kws = CATEGORIES[category]["keywords"]
    q = " OR ".join(kws)
    params = {"q": q, "pageSize": min(100,limit), "language":"en", "sortBy":"publishedAt", "apiKey": NEWSAPI_KEY}
    if country: params["q"] += f" AND ({country})"
    elif region: params["q"] += f" AND ({region})"
    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=20)
        r.raise_for_status()
        out=[]
        for a in r.json().get("articles", []):
            title=a.get("title","") or ""; desc=a.get("description","") or ""
            src_host=_src_from_url(a.get("url",""))
            score, meta = _score_item(title, desc, src_host, kws, country, region)
            out.append({
                "title":title, "summary":desc, "link":a.get("url"),
                "published":a.get("publishedAt",""), "source":src_host,
                "score": score, **meta
            })
        for it in out: it["_ts"] = _parse_dt(it["published"])
        out = _dedupe(sorted(out, key=lambda x:(x["score"], x["_ts"]), reverse=True))
        return out[:limit]
    except Exception:
        return []

def fetch_news(category: str, country: Optional[str]=None, region: Optional[str]=None, limit:int=120):
    # Try NewsAPI first; merge with RSS then re-rank (breadth + resilience)
    a = fetch_news_newsapi(category, country, region, limit)
    b = fetch_news_rss(category, country, region, limit)
    merged = (a + b) if a else b
    for it in merged:
        it["_ts"] = _parse_dt(it.get("published",""))
    merged = _dedupe(sorted(merged, key=lambda x:(x["score"], x["_ts"]), reverse=True))
    return merged[:limit]

def fetch_quotes(symbols: List[str]) -> List[Dict[str,Any]]:
    out=[]
    for s in symbols:
        try:
            hist=yf.Ticker(s).history(period="5d", interval="1d")
            if len(hist)>=2:
                last=float(hist["Close"].iloc[-1]); prev=float(hist["Close"].iloc[-2])
                chg=last-prev; pct=(chg/prev*100) if prev else 0.0
                out.append({"symbol":s,"last":round(last,2),"change":round(chg,2),"pct":round(pct,2)})
        except Exception:
            continue
    return out

def fetch_trends(category: str, geo: str) -> Dict[str,Any]:
    from pytrends.request import TrendReq
    kw = CATEGORIES[category]["keywords"][:5]
    pt = TrendReq(hl="en-US", tz=0, requests_args={"headers":{"User-Agent":"Mozilla/5.0"}})
    pt.build_payload(kw_list=kw, timeframe="today 3-m", geo=geo)
    df = pt.interest_over_time()
    if df is None or df.empty: raise RuntimeError("Empty Trends")
    if "isPartial" in df.columns: df = df.drop(columns=["isPartial"])
    labels=[d.strftime("%Y-%m-%d") for d in df.index]
    datasets=[{"label":c,"data":[int(v) if pd.notna(v) else 0 for v in df[c].tolist()]} for c in df.columns]
    return {"labels":labels,"datasets":datasets}

def news_z_dynamic(headlines: List[Dict[str,Any]], whole_feed_estimate:int=260)->float:
    N=len(headlines); baseline=max(6, 0.12*max(1,whole_feed_estimate)); std=max(1.2, baseline**0.5)
    return (N-baseline)/std

def senti_avg(headlines: List[Dict[str,Any]])->float:
    if not headlines: return 0.0
    return float(pd.Series([h["senti"] for h in headlines]).mean())

def emotion_avg(headlines: List[Dict[str,Any]])->Dict[str,float]:
    if not headlines:
        return {e:0 for e in ("anger","anticipation","disgust","fear","joy","sadness","surprise","trust")}
    df=pd.DataFrame([h["emotions"] for h in headlines])
    return {c: round(float(df[c].mean()),4) for c in df.columns}

def signals(headlines: List[Dict[str,Any]])->Dict[str,int]:
    if not headlines: return {"risk":0,"opportunity":0}
    df=pd.DataFrame(headlines)
    return {"risk": int(df["risk"].sum()), "opportunity": int(df["opportunity"].sum())}

def day_counts(headlines: List[Dict[str,Any]])->pd.DataFrame:
    if not headlines: return pd.DataFrame({"date":[],"count":[]})
    df=pd.DataFrame(headlines)
    ts=pd.to_datetime(df["published"].apply(lambda x: x if x else None), errors="coerce", utc=True)
    s = ts.dt.tz_convert("UTC").dt.date.value_counts().sort_index()
    return pd.DataFrame({"date": s.index.astype(str), "count": s.values})

def ccs_simple(news_z_v: float, s_avg: float, trends_delta: float|None, market_norm: float|None)->float:
    comps=[news_z_v, s_avg]
    if trends_delta is not None: comps.append(trends_delta)
    if market_norm is not None: comps.append(market_norm/50.0)
    val=sum(comps)/len(comps)
    return max(min(val,3.0),-3.0)

def estimated_feed_size()->int: return 260

# Back-compat aliases
def news_z(headlines): return news_z_dynamic(headlines, estimated_feed_size())
def ccs(news_z_v, s_avg, trends_delta, market_norm): return ccs_simple(news_z_v, s_avg, trends_delta, market_norm)
