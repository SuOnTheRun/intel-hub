import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
import requests
import feedparser
import yfinance as yf
from textblob import TextBlob

try:
    import praw
except Exception:
    praw = None

# ---------------------- Polygon (optional) + Yahoo Finance ----------------------

def _polygon_key() -> str | None:
    return os.getenv("POLYGON_ACCESS_KEY") or os.getenv("POLYGON_API_KEY")

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
        last = results[-1]
        prev = results[-2] if len(results) >= 2 else None
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

def _yf_snapshot_for_ticker(ticker: str) -> Dict[str, Any] | None:
    try:
        info = yf.Ticker(ticker)
        hist = info.history(period="5d", interval="1d")
        last = hist.tail(1)
        if last.empty:
            return None
        price = float(last["Close"].iloc[0])
        change = 0.0
        if len(hist) >= 2:
            prev_close = hist["Close"].iloc[-2]
            if prev_close:
                change = float((price - prev_close) / prev_close * 100.0)
        volume = int(last["Volume"].iloc[0]) if not pd.isna(last["Volume"].iloc[0]) else None
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
        time.sleep(0.15)
    return pd.DataFrame(rows).sort_values("ticker") if rows else pd.DataFrame(columns=["ticker","price","change_1d","volume","source"])

# ---------------------- News: RSS + NewsAPI ----------------------

def _rss_sources(bundle: str) -> List[str]:
    if bundle == "business_tech":
        return [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.theverge.com/rss/index.xml",
            "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        ]
    return [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    ]

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
        df["published_ts"] = pd.to_datetime(df["published"], errors="coerce")
        df = df.sort_values("published_ts", ascending=False)
    return df

def fetch_newsapi_bundle(queries: List[str], language: str = "en") -> pd.DataFrame:
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return pd.DataFrame(columns=["source","title","summary","link","published","origin"])
    rows = []
    for q in queries:
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={requests.utils.quote(q)}&language={language}&sortBy=publishedAt&pageSize=50"
        )
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
            time.sleep(0.15)
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_ts"] = pd.to_datetime(df["published"], errors="coerce")
        df = df.sort_values("published_ts", ascending=False)
    return df

def merge_news_and_dedupe(rss_df: pd.DataFrame, newsapi_df: pd.DataFrame) -> pd.DataFrame:
    if rss_df.empty and newsapi_df.empty:
        return pd.DataFrame(columns=["source","published_ts","title","sentiment","link","origin"])
    df = pd.concat([rss_df, newsapi_df], ignore_index=True)
    df = df.drop_duplicates(subset=["link"]).copy() if "link" in df.columns else df.drop_duplicates(subset=["title"]).copy()
    if "published" in df.columns and "published_ts" not in df.columns:
        df["published_ts"] = pd.to_datetime(df["published"], errors="coerce")
    return df.sort_values("published_ts", ascending=False)

# ---------------------- Google Trends ----------------------

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
            if df.empty:
                continue
            last = df.tail(1)[t].iloc[0]
            rows.append({"topic": t, "value": int(last)})
            time.sleep(0.1)
        except Exception:
            continue
    return pd.DataFrame(rows)

# ---------------------- OpenSky (positions + optional tracks) ----------------------

def fetch_opensky_air_traffic(bbox: str = None) -> pd.DataFrame:
    if not bbox:
        bbox = "5,60,35,100"
    min_lat, min_lon, max_lat, max_lon = [float(x) for x in bbox.split(",")]
    base = "https://opensky-network.org/api/states/all"
    auth = None
    if os.getenv("OPENSKY_USERNAME") and os.getenv("OPENSKY_PASSWORD"):
        auth = (os.getenv("OPENSKY_USERNAME"), os.getenv("OPENSKY_PASSWORD"))
    params = {"lamin": min_lat, "lomin": min_lon, "lamax": max_lat, "lomax": max_lon}
    r = requests.get(base, params=params, auth=auth, timeout=20)
    r.raise_for_status()
    states = (r.json() or {}).get("states", []) or []
    cols = [
        "icao24","callsign","origin_country","time_position","last_contact",
        "longitude","latitude","baro_altitude","on_ground","velocity","true_track",
        "vertical_rate","sensors","geo_altitude","squawk","spi","position_source",
        "category"
    ]
    rows = []
    for s in states:
        row = dict(zip(cols, s + [None]*(len(cols)-len(s))))
        rows.append(row)
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["latitude","longitude"])
    return df

def fetch_opensky_tracks_for_icao24(icao24: str) -> pd.DataFrame:
    """Fetch recent track (last ~1h) for a given aircraft if authenticated; anonymous may fail."""
    if not (os.getenv("OPENSKY_USERNAME") and os.getenv("OPENSKY_PASSWORD")):
        return pd.DataFrame(columns=["time","lat","lon","baro_altitude"])
    end = int(datetime.utcnow().timestamp())
    start = end - 3600
    base = "https://opensky-network.org/api/tracks/all"
    auth = (os.getenv("OPENSKY_USERNAME"), os.getenv("OPENSKY_PASSWORD"))
    r = requests.get(base, params={"icao24": icao24, "time": end}, auth=auth, timeout=20)
    if r.status_code != 200:
        return pd.DataFrame(columns=["time","lat","lon","baro_altitude"])
    data = r.json() or {}
    path = data.get("path") or []
    rows = [{"time": p.get("time"), "lat": p.get("latitude"), "lon": p.get("longitude"), "baro_altitude": p.get("baro_altitude")} for p in path]
    return pd.DataFrame(rows)

# ---------------------- Reddit (optional) ----------------------

def fetch_reddit_posts_if_configured(queries: List[str]) -> pd.DataFrame:
    if not praw:
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])
    cid = os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("REDDIT_CLIENT_SECRET")
    uag = os.getenv("REDDIT_USER_AGENT")
    if not (cid and csec and uag):
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])
    reddit = praw.Reddit(client_id=cid, client_secret=csec, user_agent=uag, check_for_async=False)
    rows = []
    for q in queries:
        for post in reddit.subreddit("all").search(q, sort="new", time_filter="day", limit=50):
            rows.append({
                "query": q,
                "subreddit": str(post.subreddit),
                "title": post.title,
                "score": int(post.score),
                "url": f"https://reddit.com{post.permalink}",
                "created_utc": pd.to_datetime(post.created_utc, unit="s")
            })
        time.sleep(0.1)
    return pd.DataFrame(rows)

# ---------------------- GDELT (no key) ----------------------

def fetch_gdelt_events(queries: List[str]) -> pd.DataFrame:
    """
    Fetches recent GDELT 'Events' 2.1 API for given queries; lightweight and real.
    """
    rows = []
    for q in queries[:5]:
        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            f"?query={requests.utils.quote(q)}&mode=ArtList&format=json&maxrecords=50&timespan=72hours"
        )
        try:
            r = requests.get(url, timeout=25)
            r.raise_for_status()
            arts = (r.json() or {}).get("articles") or []
            for a in arts:
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
            time.sleep(0.15)
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df["published_ts"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
        df = df.sort_values("published_ts", ascending=False)
    return df
