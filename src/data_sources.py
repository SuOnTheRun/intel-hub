import os, time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import requests
import feedparser
import yfinance as yf
from textblob import TextBlob

# Optional reddit
try:
    import praw
except Exception:
    praw = None

# Optional Streamlit cache decorator (no-op if not running under Streamlit)
try:
    import streamlit as st
    cache = st.cache_data
except Exception:  # pragma: no cover
    def cache(*args, **kwargs):
        def wrap(fn): return fn
        return wrap

# ---------------------- Helpers ----------------------

def _utcify(series):
    return pd.to_datetime(series, errors="coerce", utc=True)

# ---------------------- Polygon + Yahoo (markets) ----------------------

def _polygon_key() -> str | None:
    return os.getenv("POLYGON_ACCESS_KEY") or os.getenv("POLYGON_API_KEY")

@cache(ttl=300)
def _polygon_agg_for_ticker(ticker: str) -> Dict[str, Any] | None:
    api_key = _polygon_key()
    if not api_key:
        return None
    end = datetime.utcnow().date()
    start = end - timedelta(days=7)
    url = (
        f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/"
        f"{start:%Y-%m-%d}/{end:%Y-%m-%d}?adjusted=true&limit=10&apiKey={api_key}"
    )
    try:
        r = requests.get(url, timeout=25)
        r.raise_for_status()
        results = (r.json() or {}).get("results") or []
        if not results:
            return None
        last = results[-1]; prev = results[-2] if len(results) >= 2 else None
        out = {
            "ticker": ticker,
            "price": float(last.get("c", 0.0)),
            "volume": int(last.get("v", 0)) if last.get("v") is not None else None,
            "source": "polygon",
        }
        if prev and prev.get("c"):
            out["change_1d"] = ((last["c"] - prev["c"]) / prev["c"]) * 100.0
        else:
            out["change_1d"] = 0.0
        return out
    except Exception:
        return None

@cache(ttl=300)
def _yf_snapshot_for_ticker(ticker: str) -> Dict[str, Any] | None:
    try:
        info = yf.Ticker(ticker)
        hist = info.history(period="5d", interval="1d")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
        change = ((price - prev_close) / prev_close) * 100.0 if prev_close else 0.0
        volume = int(hist["Volume"].iloc[-1]) if not pd.isna(hist["Volume"].iloc[-1]) else None
        return {"ticker": ticker, "price": price, "change_1d": change, "volume": volume, "source": "yfinance"}
    except Exception:
        return None

def fetch_market_snapshot(tickers: List[str]) -> pd.DataFrame:
    rows = []
    use_polygon = bool(_polygon_key())
    for t in tickers:
        row = _polygon_agg_for_ticker(t) if use_polygon else None
        if row is None:
            row = _yf_snapshot_for_ticker(t)
        if row:
            rows.append(row)
        time.sleep(0.1)
    return pd.DataFrame(rows).sort_values("ticker") if rows else pd.DataFrame(columns=["ticker","price","change_1d","volume","source"])

# ---------------------- News: RSS + NewsAPI ----------------------

def _rss_sources(bundle: str) -> List[str]:
    if bundle == "business_tech":
        return [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.cnbc.com/id/10001147/device/rss/rss.html",
            "https://www.ft.com/rss/home/asia",   # FT Asia
        ]
    return [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    ]

@cache(ttl=300)
def fetch_rss_bundle(bundle: str) -> pd.DataFrame:
    rows = []
    for url in _rss_sources(bundle):
        parsed = feedparser.parse(url)
        for e in parsed.entries[:60]:
            rows.append({
                "source": parsed.feed.get("title", ""),
                "title": e.get("title", ""),
                "summary": e.get("summary", ""),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
                "origin": "rss",
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_ts"] = _utcify(df["published"])
        df = df.sort_values("published_ts", ascending=False)
    return df

def _expanded_queries(region_term: str, topics: List[str], extra_keywords: List[str]) -> List[str]:
    base = [region_term] + topics
    for k in extra_keywords:
        base.append(f"{region_term} {k}")
    return list(dict.fromkeys([q for q in base if q]))

@cache(ttl=300)
def fetch_newsapi_bundle(query_terms: List[str], language: str = "en") -> pd.DataFrame:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return pd.DataFrame(columns=["source","title","summary","link","published","origin"])
    rows = []
    for q in query_terms:
        url = ("https://newsapi.org/v2/everything"
               f"?q={requests.utils.quote(q)}&language={language}&sortBy=publishedAt&pageSize=100")
        try:
            r = requests.get(url, headers={"X-Api-Key": api_key}, timeout=25)
            r.raise_for_status()
            for a in (r.json().get("articles") or []):
                rows.append({
                    "source": (a.get("source") or {}).get("name", ""),
                    "title": a.get("title", ""),
                    "summary": a.get("description", ""),
                    "link": a.get("url", ""),
                    "published": a.get("publishedAt", ""),
                    "origin": "newsapi",
                    "query": q,
                })
            time.sleep(0.1)
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_ts"] = _utcify(df["published"])
        df = df.drop_duplicates(subset=["link"]).sort_values("published_ts", ascending=False)
    return df

def merge_news_and_dedupe(rss_df: pd.DataFrame, newsapi_df: pd.DataFrame) -> pd.DataFrame:
    if (rss_df is None or rss_df.empty) and (newsapi_df is None or newsapi_df.empty):
        return pd.DataFrame(columns=["source","published_ts","title","sentiment","link","origin"])
    df = pd.concat([rss_df, newsapi_df], ignore_index=True)
    df = (df.drop_duplicates(subset=["link"]) if "link" in df.columns else
          df.drop_duplicates(subset=["title"]))
    if "published_ts" not in df.columns:
        df["published_ts"] = _utcify(df.get("published"))
    else:
        df["published_ts"] = _utcify(df["published_ts"])
    return df.sort_values("published_ts", ascending=False)

# ---------------------- Google Trends ----------------------

@cache(ttl=300)
def fetch_google_trends(topics: List[str]) -> pd.DataFrame:
    try:
        from pytrends.request import TrendReq
    except Exception:
        return pd.DataFrame(columns=["topic","value"])
    pytrends = TrendReq(hl="en-US", tz=330)
    rows = []
    for t in topics:
        try:
            pytrends.build_payload([t], timeframe="now 7-d", geo="")
            df = pytrends.interest_over_time()
            if df.empty: continue
            last = df.tail(1)[t].iloc[0]
            rows.append({"topic": t, "value": int(last)})
            time.sleep(0.05)
        except Exception:
            continue
    return pd.DataFrame(rows)

# ---------------------- OpenSky ----------------------

@cache(ttl=120)
def fetch_opensky_air_traffic(bbox: str = None, allow_global_fallback: bool = True) -> pd.DataFrame:
    base = "https://opensky-network.org/api/states/all"
    auth = None
    if os.getenv("OPENSKY_USERNAME") and os.getenv("OPENSKY_PASSWORD"):
        auth = (os.getenv("OPENSKY_USERNAME"), os.getenv("OPENSKY_PASSWORD"))
    params = {}
    if bbox:
        min_lat, min_lon, max_lat, max_lon = [float(x) for x in bbox.split(",")]
        params = {"lamin": min_lat, "lomin": min_lon, "lamax": max_lat, "lomax": max_lon}
    r = requests.get(base, params=params, auth=auth, timeout=20)
    if r.status_code != 200 and allow_global_fallback:
        r = requests.get(base, timeout=20)  # real global fallback
    r.raise_for_status()
    states = (r.json() or {}).get("states", []) or []
    cols = [
        "icao24","callsign","origin_country","time_position","last_contact",
        "longitude","latitude","baro_altitude","on_ground","velocity","true_track",
        "vertical_rate","sensors","geo_altitude","squawk","spi","position_source","category"
    ]
    rows = []
    for s in states:
        row = dict(zip(cols, s + [None]*(len(cols)-len(s))))
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["latitude","longitude"])
    return df

@cache(ttl=120)
def fetch_opensky_tracks_for_icao24(icao24: str) -> pd.DataFrame:
    if not (os.getenv("OPENSKY_USERNAME") and os.getenv("OPENSKY_PASSWORD")):
        return pd.DataFrame(columns=["time","lat","lon","baro_altitude"])
    base = "https://opensky-network.org/api/tracks/all"
    auth = (os.getenv("OPENSKY_USERNAME"), os.getenv("OPENSKY_PASSWORD"))
    now = int(datetime.utcnow().timestamp())
    r = requests.get(base, params={"icao24": icao24, "time": now}, auth=auth, timeout=20)
    if r.status_code != 200:
        return pd.DataFrame(columns=["time","lat","lon","baro_altitude"])
    path = (r.json() or {}).get("path") or []
    rows = [{"time": p.get("time"), "lat": p.get("latitude"), "lon": p.get("longitude"), "baro_altitude": p.get("baro_altitude")} for p in path]
    return pd.DataFrame(rows)

# ---------------------- Reddit ----------------------

@cache(ttl=300)
def fetch_reddit_posts_if_configured(queries: List[str]) -> pd.DataFrame:
    if not praw:
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])
    cid = os.getenv("REDDIT_CLIENT_ID"); csec = os.getenv("REDDIT_CLIENT_SECRET"); uag = os.getenv("REDDIT_USER_AGENT")
    if not (cid and csec and uag):
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])
    reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=uag, check_for_async=False)
    rows = []
    for q in queries:
        for post in reddit.subreddit("all").search(q, sort="new", time_filter="day", limit=50):
            rows.append({
                "query": q, "subreddit": str(post.subreddit), "title": post.title, "score": int(post.score),
                "url": f"https://reddit.com{post.permalink}", "created_utc": pd.to_datetime(post.created_utc, unit="s")
            })
        time.sleep(0.05)
    return pd.DataFrame(rows)

# ---------------------- GDELT (doc API) ----------------------

@cache(ttl=300)
def fetch_gdelt_events(queries: List[str]) -> pd.DataFrame:
    rows = []
    for q in queries[:6]:
        url = ("https://api.gdeltproject.org/api/v2/doc/doc"
               f"?query={requests.utils.quote(q)}&mode=ArtList&format=json&maxrecords=75&timespan=72hours")
        try:
            r = requests.get(url, timeout=25)
            r.raise_for_status()
            for a in (r.json() or {}).get("articles", []) or []:
                rows.append({
                    "source": a.get("sourceCommonName", ""),
                    "title": a.get("title", ""),
                    "summary": a.get("seendate", ""),
                    "link": a.get("url", ""),
                    "published": a.get("seendate", ""),
                    "origin": "gdelt",
                    "location": a.get("location", ""),
                    "theme": a.get("themes", ""),
                })
            time.sleep(0.05)
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_ts"] = _utcify(df["published"])
        df = df.sort_values("published_ts", ascending=False)
    return df
