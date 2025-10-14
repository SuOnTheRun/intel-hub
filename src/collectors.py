import re, math, requests, feedparser, yfinance as yf
from typing import List, Dict, Any, Optional
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
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
    "consumer_staples":{"name":"Consumer Staples","keywords":["grocery","beverages","household","personal care","retail"],"tickers":["XLP"]},
    "energy":{"name":"Energy","keywords":["oil","gas","refinery","opec","renewables","power"],"tickers":["XLE"]},
    "technology":{"name":"Technology","keywords":["ai","chip","semiconductor","software","cloud","datacenter"],"tickers":["XLK"]},
    "automotive":{"name":"Automotive","keywords":["auto","ev","car","cars","battery","dealership","supplier"],"tickers":["CARZ"]},
    "financials":{"name":"Financials","keywords":["bank","fintech","credit","payments","lending"],"tickers":["XLF"]},
    "media":{"name":"Media & Advertising","keywords":["advertising","adtech","programmatic","ctv","streaming","social"],"tickers":["XLC"]},
    "healthcare":{"name":"Healthcare","keywords":["pharma","drug","biotech","vaccine","diagnostics"],"tickers":["XLV"]},
}

# BBC / Al Jazeera / AP / DW / CNBC / FT / Reuters
RSS_FEEDS = [
    # Global
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://apnews.com/hub/apf-topnews?utm_source=rss",              # AP top
    "https://rss.dw.com/rdf/rss-en-ger",                              # DW Global
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",           # CNBC Top News
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",           # CNBC Tech
    "https://www.ft.com/rss/home/uk",                                 # FT
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

def _keyword(text: str, kws: List[str]) -> bool:
    b = text.lower()
    return any(re.search(rf"\b{k}\b", b) for k in kws)

def _score(title: str, summary: str) -> Dict[str, float]:
    s = analyzer.polarity_scores(title)["compound"]
    emo = emotion_scores(f"{title}. {summary}")
    return {"senti": float(s), "emotions": emo}

def fetch_news_rss(category: str, country: Optional[str], region: Optional[str], limit: int=80) -> List[Dict[str,Any]]:
    kws=CATEGORIES[category]["keywords"]; out=[]
    for url in RSS_FEEDS:
        try:
            for e in feedparser.parse(url).entries[:60]:
                title=e.get("title","") or ""; summary=e.get("summary","") or ""
                blob=f"{title} {summary}"
                if _keyword(blob, kws) and _geo_match(blob, country, region):
                    sc=_score(title, summary)
                    out.append({"title":title,"summary":summary,"link":e.get("link"),
                                "published":e.get("published",""),"source":re.sub(r"^https?://(www\\.)?","",url).split('/')[0],
                                **sc})
                if len(out)>=limit: break
        except Exception:
            continue
    return out

def fetch_news_newsapi(category: str, country: Optional[str], region: Optional[str], limit:int=60) -> List[Dict[str,Any]]:
    if not NEWSAPI_KEY: 
        return []
    q = " OR ".join(CATEGORIES[category]["keywords"])
    params = {"q": q, "pageSize": min(100,limit), "language":"en", "sortBy":"publishedAt", "apiKey": NEWSAPI_KEY}
    if country: params["q"] += f" AND ({country})"
    elif region: params["q"] += f" AND ({region})"
    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=20)
        r.raise_for_status()
        out=[]
        for a in r.json().get("articles", []):
            title=a.get("title","") or ""; desc=a.get("description","") or ""
            if not _keyword(f"{title} {desc}", CATEGORIES[category]["keywords"]): 
                continue
            sc=_score(title, desc)
            out.append({"title":title,"summary":desc,"link":a.get("url"),
                        "published":a.get("publishedAt",""),
                        "source":a.get("source",{}).get("name",""),
                        **sc})
        return out[:limit]
    except Exception:
        return []

def fetch_news(category: str, country: Optional[str]=None, region: Optional[str]=None, limit:int=80):
    items = fetch_news_newsapi(category, country, region, limit)
    if not items:
        items = fetch_news_rss(category, country, region, limit)
    return items

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

def news_z_dynamic(headlines: List[Dict[str,Any]], whole_feed_estimate:int=200)->float:
    N=len(headlines); baseline=max(5, 0.12*max(1,whole_feed_estimate)); std=max(1.0, baseline**0.5)
    return (N-baseline)/std

def senti_avg(headlines: List[Dict[str,Any]])->float:
    if not headlines: return 0.0
    return float(pd.Series([h["senti"] for h in headlines]).mean())

def emotion_avg(headlines: List[Dict[str,Any]])->Dict[str,float]:
    if not headlines: 
        return {e:0 for e in ("anger","anticipation","disgust","fear","joy","sadness","surprise","trust")}
    df=pd.DataFrame([h["emotions"] for h in headlines])
    return {c: round(float(df[c].mean()),4) for c in df.columns}

def ccs_simple(news_z_v: float, s_avg: float, trends_delta: float|None, market_norm: float|None)->float:
    comps=[news_z_v, s_avg]
    if trends_delta is not None: comps.append(trends_delta)
    if market_norm is not None: comps.append(market_norm/50.0)
    val=sum(comps)/len(comps)
    return max(min(val,3.0),-3.0)

def estimated_feed_size()->int:
    # higher baseline now that we pull from many feeds
    return 200

# --- Backward-compat aliases (safe to keep)
def news_z(headlines): return news_z_dynamic(headlines, estimated_feed_size())
def ccs(news_z_v, s_avg, trends_delta, market_norm): return ccs_simple(news_z_v, s_avg, trends_delta, market_norm)
