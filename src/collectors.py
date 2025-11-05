# src/collectors.py — coverage-first, capped, cached, UTC-safe (fixed .str.strip)

from __future__ import annotations
import os, json, time, random, urllib.request
from typing import Dict, List, Tuple
from urllib.parse import urlparse
import pandas as pd

# Prefer feedparser; fall back to minimal XML
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None
import xml.etree.ElementTree as ET

# ---- Tunables for Render free-tier ----
MAX_TOTAL_FEEDS         = 64   # total external feeds per refresh
MANDATORY_PER_CATEGORY  = 2    # always include first N feeds for every category
OPTIONAL_PER_CATEGORY   = 2    # then rotate up to this many more per category
MAX_ITEMS_PER_FEED      = 60
PER_REQUEST_TIMEOUT     = 5
DISK_CACHE_TTL_SEC      = 600  # 10 minutes
DISK_CACHE_DIR          = "data"
DISK_CACHE_PATH         = os.path.join(DISK_CACHE_DIR, "news_cache.json")

# ---- Time parsing (tz-safe → UTC) ----
from dateutil import parser as dtparser
from datetime import timezone, timedelta

_TZINFOS = {
    "UTC": 0, "GMT": 0,
    "EST": -5*3600, "EDT": -4*3600,
    "CST": -6*3600, "CDT": -5*3600,
    "MST": -7*3600, "MDT": -6*3600,
    "PST": -8*3600, "PDT": -7*3600,
    "BST": 1*3600, "WET": 0, "WEST": 1*3600,
    "CET": 1*3600, "CEST": 2*3600, "EET": 2*3600, "EEST": 3*3600,
    "IST": 19800, "JST": 9*3600, "KST": 9*3600, "HKT": 8*3600, "SGT": 8*3600,
    "AEST": 10*3600, "AEDT": 11*3600,
}

def _to_utc(ts_str: str) -> pd.Timestamp:
    if not ts_str:
        return pd.Timestamp.utcnow().tz_localize("UTC")
    try:
        dt = dtparser.parse(ts_str, tzinfos={k: timedelta(seconds=v) for k, v in _TZINFOS.items()})
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return pd.Timestamp(dt.astimezone(timezone.utc))
    except Exception:
        return pd.Timestamp.utcnow().tz_localize("UTC")

# ---- Disk cache ----
def _cache_write(df: pd.DataFrame):
    try:
        os.makedirs(DISK_CACHE_DIR, exist_ok=True)
        payload = {
            "ts": time.time(),
            "rows": df.assign(published_dt=df["published_dt"].astype(str)).to_dict(orient="records"),
        }
        with open(DISK_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        pass

def _cache_read() -> pd.DataFrame | None:
    try:
        if not os.path.exists(DISK_CACHE_PATH):
            return None
        with open(DISK_CACHE_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - float(payload.get("ts", 0)) > DISK_CACHE_TTL_SEC:
            return None
        rows = payload.get("rows", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)
        df["published_dt"] = pd.to_datetime(df["published_dt"], utc=True, errors="coerce").fillna(
            pd.Timestamp.utcnow().tz_localize("UTC")
        )
        return df.sort_values("published_dt", ascending=False).reset_index(drop=True)
    except Exception:
        return None

# ---- Helpers ----
def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""

def _fetch_feed(url: str, max_items: int = MAX_ITEMS_PER_FEED, timeout: int = PER_REQUEST_TIMEOUT) -> List[Dict]:
    items: List[Dict] = []
    try:
        if feedparser:
            d = feedparser.parse(url, request_headers={"User-Agent": "intel-hub/1.0"})
            for e in d.entries[:max_items]:
                title = getattr(e, "title", "") or ""
                link  = getattr(e, "link", "") or ""
                desc  = getattr(e, "summary", "") or getattr(e, "description", "") or ""
                if getattr(e, "published", None):
                    published = _to_utc(getattr(e, "published"))
                elif getattr(e, "updated", None):
                    published = _to_utc(getattr(e, "updated"))
                else:
                    try:
                        t = time.mktime(getattr(e, "published_parsed"))
                        published = pd.Timestamp(t, unit="s", tz="UTC")
                    except Exception:
                        published = pd.Timestamp.utcnow().tz_localize("UTC")
                items.append({"title": title, "link": link, "summary": desc, "published_dt": published})
            return items

        # Fallback XML
        req = urllib.request.Request(url, headers={"User-Agent": "intel-hub/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
        root = ET.fromstring(data)
        nodes = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for n in nodes[:max_items]:
            title = (n.findtext("title") or n.findtext("{http://www.w3.org/2005/Atom}title") or "").strip()
            link_node = n.find("link") or n.find("{http://www.w3.org/2005/Atom}link")
            link = (link_node.text or link_node.get("href")) if link_node is not None else ""
            desc = (n.findtext("description") or n.findtext("{http://www.w3.org/2005/Atom}summary") or "")[:1000]
            pub  = n.findtext("pubDate") or n.findtext("{http://www.w3.org/2005/Atom}updated") or ""
            items.append({"title": title, "link": link, "summary": desc, "published_dt": _to_utc(pub)})
    except Exception:
        pass
    return items

# ---- Planning (coverage-first) ----
def _plan_feeds(catalog: Dict[str, List[str]]) -> List[Tuple[str, str]]:
    mandatory: List[Tuple[str, str]] = []
    optional:  List[Tuple[str, str]] = []

    for cat, urls in catalog.items():
        urls = list(urls)
        for u in urls[:MANDATORY_PER_CATEGORY]:
            mandatory.append((cat, u))
        rest = urls[MANDATORY_PER_CATEGORY:]
        random.shuffle(rest)
        for u in rest[:OPTIONAL_PER_CATEGORY]:
            optional.append((cat, u))

    random.shuffle(mandatory)
    random.shuffle(optional)
    plan = mandatory + optional
    return plan[:MAX_TOTAL_FEEDS]

# ---- Public API ----
def get_news_dataframe(catalog_path: str) -> pd.DataFrame:
    """
    Returns DataFrame with: category, source, title, link, summary, published_dt (UTC tz-aware).
    Uses disk cache (10 min) and coverage-first planning so every category gets at least some headlines.
    """
    # Serve from cache if fresh
    cached = _cache_read()
    if cached is not None and not cached.empty:
        return cached

    # Load catalog
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception:
        catalog = {}

    planned = _plan_feeds(catalog)

    rows: List[Dict] = []
    for category, url in planned:
        for it in _fetch_feed(url):
            rows.append({
                "category": category,
                "source": _domain(it.get("link", "")),
                "title": it.get("title", ""),
                "link": it.get("link", ""),
                "summary": it.get("summary", ""),
                "published_dt": it.get("published_dt", pd.Timestamp.utcnow().tz_localize("UTC")),
            })

    df = pd.DataFrame(rows)
    if df.empty:
        stale = _cache_read()
        return stale if stale is not None else df

    # ---- CLEANING (fixed) ----
    try:
        df["title"] = (
            df["title"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        )
        df["summary"] = df["summary"].fillna("").astype(str)
    except Exception:
        # Never let a cleaning error nuke the snapshot
        pass

    try:
        df["published_dt"] = pd.to_datetime(df["published_dt"], utc=True, errors="coerce").fillna(
            pd.Timestamp.utcnow().tz_localize("UTC")
        )
    except Exception:
        df["published_dt"] = pd.Timestamp.utcnow().tz_localize("UTC")

    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)

    _cache_write(df)
    return df
# ------------------------------
# US-SCOPED COLLECTORS (ADD-ON)
# ------------------------------
import os
import io
import gzip
import time
import json
import math
import requests
import pandas as pd
import feedparser
from datetime import datetime, timedelta, timezone

# pytrends
try:
    from pytrends.request import TrendReq
except Exception:
    TrendReq = None

# FRED
try:
    from fredapi import Fred
except Exception:
    Fred = None

_NAIVE_NOW = datetime.utcnow().replace(tzinfo=timezone.utc)

def _safe_df(df: pd.DataFrame, cols=None) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=cols or [])
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=cols or [])
    return df

def _to_dt(x):
    try:
        return pd.to_datetime(x, utc=True)
    except Exception:
        return pd.NaT

# 1) Google News RSS (US)
def collect_us_google_news(categories: list[str] | None = None, max_items: int = 400) -> pd.DataFrame:
    """
    Pull top US-edition headlines across general + optional category terms.
    No API key. Real data. Returns columns: [published, source, title, link, summary, category]
    """
    base_feeds = [
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    ]
    categories = categories or []
    # category-specific editions (append queries)
    for cat in categories:
        base_feeds.append(f"https://news.google.com/rss/search?q={requests.utils.quote(cat)}&hl=en-US&gl=US&ceid=US:en")

    rows = []
    for url in base_feeds:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:max_items]:
                rows.append({
                    "published": _to_dt(getattr(e, "published", getattr(e, "updated", None))),
                    "source": getattr(getattr(e, "source", {}), "title", None) or getattr(e, "source", None),
                    "title": getattr(e, "title", None),
                    "link": getattr(e, "link", None),
                    "summary": getattr(e, "summary", None),
                    "category": "General" if url.endswith("US:en") else "Search",
                })
        except Exception:
            continue
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.dropna(subset=["title"]).drop_duplicates(subset=["title"]).sort_values("published", ascending=False)
    return df

# 2) GDELT last 48h, filter to US
def collect_us_gdelt_events(hours_back: int = 48) -> pd.DataFrame:
    """
    Pull recent GDELT events (CSV) and filter where ActionGeo_CountryCode == 'US'.
    Real data (no key). Returns a compact frame used for incident heatmaps.
    """
    end = _NAIVE_NOW
    start = end - timedelta(hours=hours_back)

    # GDELT 2.1 hourly files pattern
    # Example: http://data.gdeltproject.org/gdeltv2/20251104010000.export.CSV.zip
    # We'll iterate per hour and concatenate (conservative upper bound)
    def _hourly_keys(start_dt, end_dt):
        t = start_dt.replace(minute=0, second=0, microsecond=0)
        while t <= end_dt:
            yield t.strftime("%Y%m%d%H%M%S")
            t += timedelta(hours=1)

    frames = []
    for ts in _hourly_keys(start, end):
        url = f"http://data.gdeltproject.org/gdeltv2/{ts}.export.CSV.zip"
        try:
            r = requests.get(url, timeout=20)
            if r.status_code != 200 or not r.content:
                continue
            z = io.BytesIO(r.content)
            import zipfile
            with zipfile.ZipFile(z) as zf:
                names = zf.namelist()
                if not names:
                    continue
                with zf.open(names[0]) as fh:
                    df = pd.read_csv(fh, sep="\t", header=None, low_memory=False)
                    # Columns per schema (keep only the essentials we need)
                    df = df.rename(columns={
                        0:"GLOBALEVENTID", 1:"SQLDATE", 8:"Actor1Code", 15:"Actor2Code",
                        26:"IsRootEvent", 27:"EventCode", 30:"NumMentions", 31:"NumSources",
                        32:"NumArticles", 33:"AvgTone", 34:"Actor1Geo_Type", 35:"Actor1Geo_FullName",
                        37:"Actor1Geo_CountryCode", 40:"Actor2Geo_Type", 41:"Actor2Geo_FullName",
                        43:"Actor2Geo_CountryCode", 51:"ActionGeo_Type", 52:"ActionGeo_FullName",
                        53:"ActionGeo_CountryCode", 57:"DATEADDED"
                    })
                    df = df[df["ActionGeo_CountryCode"] == "US"]
                    if df.empty: 
                        continue
                    df["ts"] = pd.to_datetime(df["DATEADDED"], format="%Y%m%d%H%M%S", utc=True, errors="coerce")
                    frames.append(df[[
                        "ts","GLOBALEVENTID","EventCode","NumMentions","NumArticles","AvgTone",
                        "ActionGeo_FullName","ActionGeo_CountryCode"
                    ]])
        except Exception:
            continue
        # be polite
        time.sleep(0.3)
    if not frames:
        return pd.DataFrame(columns=["ts","GLOBALEVENTID","EventCode","NumMentions","NumArticles","AvgTone","ActionGeo_FullName","ActionGeo_CountryCode"])
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values("ts", ascending=False)

# 3) Google Trends (purchase intent)
_PURCHASE_KEYWORDS = [
    "buy now", "discount", "coupon", "financing", "interest rate car",
    "best smartphone", "gym membership", "air conditioner", "home loan",
    "fast food near me", "restaurant deals", "tv sale", "travel deals"
]

def collect_us_trends(keywords: list[str] | None = None, days: int = 90) -> pd.DataFrame:
    """
    pytrends interest_over_time for US. Returns weekly/daily interest per term with a combined long frame.
    """
    if TrendReq is None:
        return pd.DataFrame(columns=["date","term","interest"])
    kw = keywords or _PURCHASE_KEYWORDS
    pytrends = TrendReq(hl="en-US", tz=360)
    start = (_NAIVE_NOW - timedelta(days=days)).strftime("%Y-%m-%d")
    timeframe = f"{start} { _NAIVE_NOW.strftime('%Y-%m-%d') }"
    rows = []
    # pytrends only takes 5 terms per batch
    for i in range(0, len(kw), 5):
        group = kw[i:i+5]
        try:
            pytrends.build_payload(group, cat=0, timeframe=timeframe, geo="US")
            df = pytrends.interest_over_time()
            if df is None or df.empty:
                continue
            df = df.reset_index().rename(columns={"date":"date"})
            for g in group:
                if g in df.columns:
                    part = df[["date", g]].rename(columns={g:"interest"})
                    part["term"] = g
                    rows.append(part[["date","term","interest"]])
        except Exception:
            continue
        time.sleep(0.3)
    if not rows:
        return pd.DataFrame(columns=["date","term","interest"])
    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"], utc=True)
    return out.sort_values("date")

# 4) FRED macro series (US confidence, sales, unemployment)
_FRED_SERIES = {
    "UMCSENT": "consumer_sentiment", # University of Michigan: Consumer Sentiment
    "RSAFS": "retail_sales",         # Retail Sales: All Businesses (SA, $)
    "UNRATE": "unemployment_rate",   # Unemployment Rate
}

def collect_us_fred() -> pd.DataFrame:
    """
    Requires FRED_API_KEY in env (free). Returns a tidy frame: [date, series, value]
    """
    if Fred is None:
        return pd.DataFrame(columns=["date","series","value"])
    key = os.environ.get("FRED_API_KEY", "").strip()
    if not key:
        # Return empty but real schema; UI will soft-fail without breaking.
        return pd.DataFrame(columns=["date","series","value"])
    fred = Fred(api_key=key)
    rows = []
    for sid, name in _FRED_SERIES.items():
        try:
            s = fred.get_series(sid)
            df = s.reset_index()
            df.columns = ["date","value"]
            df["date"] = pd.to_datetime(df["date"], utc=True)
            df["series"] = name
            rows.append(df[["date","series","value"]])
        except Exception:
            continue
        time.sleep(0.2)
    if not rows:
        return pd.DataFrame(columns=["date","series","value"])
    out = pd.concat(rows, ignore_index=True).sort_values(["series","date"])
    return out
