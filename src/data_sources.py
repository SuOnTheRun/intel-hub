import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any

import pandas as pd
import requests
import feedparser
import yfinance as yf
from textblob import TextBlob

# Optional: Reddit & OpenSky
try:
    import praw
except Exception:
    praw = None

# -------------- Markets (yfinance: real, no key) --------------
def fetch_market_snapshot(tickers: List[str]) -> pd.DataFrame:
    rows = []
    for t in tickers:
        try:
            info = yf.Ticker(t)
            hist = info.history(period="5d", interval="1d")
            last = hist.tail(1)
            if last.empty:
                continue
            row = {
                "ticker": t,
                "price": float(last["Close"].iloc[0]),
                "change_1d": float((last["Close"].iloc[0] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2] * 100) if len(hist) >= 2 else 0.0,
                "volume": int(last["Volume"].iloc[0]) if not pd.isna(last["Volume"].iloc[0]) else None
            }
            rows.append(row)
        except Exception:
            # skip bad tickers silently
            continue
        time.sleep(0.2)  # be polite
    df = pd.DataFrame(rows).sort_values("ticker") if rows else pd.DataFrame(columns=["ticker","price","change_1d","volume"])
    return df

# -------------- News via RSS (real, no key) --------------
def _rss_sources(bundle: str) -> List[str]:
    if bundle == "business_tech":
        return [
            "https://feeds.reuters.com/reuters/businessNews",
            "https://feeds.arstechnica.com/arstechnica/index",
            "https://www.theverge.com/rss/index.xml",
            "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        ]
    # default bundle
    return [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    ]

def fetch_rss_bundle(bundle: str) -> pd.DataFrame:
    urls = _rss_sources(bundle)
    rows = []
    for url in urls:
        parsed = feedparser.parse(url)
        for e in parsed.entries[:50]:
            rows.append({
                "source": parsed.feed.get("title", ""),
                "title": e.get("title", ""),
                "summary": e.get("summary", ""),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        # normalize time if available
        df["published_ts"] = pd.to_datetime(df["published"], errors="coerce")
        df = df.sort_values("published_ts", ascending=False)
    return df

def compute_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    def s(text):
        try:
            return TextBlob(str(text)).sentiment.polarity
        except Exception:
            return 0.0
    df = df.copy()
    df["sentiment"] = df["title"].fillna("").apply(s)
    return df

# -------------- Google Trends (pytrends: real, no key) --------------
def fetch_google_trends(topics: List[str]) -> pd.DataFrame:
    try:
        from pytrends.request import TrendReq
    except Exception:
        # user may not have pytrends installed if requirements missing
        return pd.DataFrame(columns=["topic","query","value"])
    pytrends = TrendReq(hl="en-US", tz=330)  # IST offset
    rows = []
    for t in topics:
        try:
            pytrends.build_payload([t], timeframe="now 7-d", geo="")
            df = pytrends.interest_over_time()
            if df.empty:
                continue
            last = df.tail(1)[t].iloc[0]
            rows.append({"topic": t, "query": t, "value": int(last)})
            time.sleep(0.2)
        except Exception:
            continue
    return pd.DataFrame(rows)

# -------------- OpenSky (real; anonymous with limits or with creds) --------------
def fetch_opensky_air_traffic(bbox: str = None) -> pd.DataFrame:
    """
    Pulls current state vectors. Anonymous is rate-limited; if OPENSKY_USERNAME/PASSWORD
    are set in Render env, authenticated calls are used.

    bbox format: "min_lat,min_lon,max_lat,max_lon"
    If not provided, default to India-ish wide bbox to make it meaningful for APAC work.
    """
    if not bbox:
        bbox = "5,60,35,100"  # roughly India & neighborhood
    min_lat, min_lon, max_lat, max_lon = [float(x) for x in bbox.split(",")]

    base = "https://opensky-network.org/api/states/all"
    auth = None
    if os.getenv("OPENSKY_USERNAME") and os.getenv("OPENSKY_PASSWORD"):
        auth = (os.getenv("OPENSKY_USERNAME"), os.getenv("OPENSKY_PASSWORD"))

    params = {"lamin": min_lat, "lomin": min_lon, "lamax": max_lat, "lomax": max_lon}
    r = requests.get(base, params=params, auth=auth, timeout=20)
    r.raise_for_status()
    js = r.json()
    states = js.get("states", []) or []
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
    return pd.DataFrame(rows)

# -------------- Reddit (optional, real) --------------
def fetch_reddit_posts_if_configured(queries: List[str]) -> pd.DataFrame:
    if not praw:
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])
    cid = os.getenv("REDDIT_CLIENT_ID")
    csec = os.getenv("REDDIT_CLIENT_SECRET")
    uag = os.getenv("REDDIT_USER_AGENT")
    if not (cid and csec and uag):
        return pd.DataFrame(columns=["subreddit","title","score","url","created_utc"])

    reddit = praw.Reddit(
        client_id=cid, client_secret=csec, user_agent=uag, check_for_async=False
    )
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
        time.sleep(0.2)
    return pd.DataFrame(rows)
