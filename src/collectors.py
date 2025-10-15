# src/collectors.py — capped, cached feed collection with UTC-safe dates
from __future__ import annotations
import os, json, time, random, urllib.request
from typing import Dict, List
from urllib.parse import urlparse
import pandas as pd

# Prefer feedparser; fall back to minimal XML
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None
import xml.etree.ElementTree as ET

# ---- Tunables (keep Render free-tier happy) ----
MAX_TOTAL_FEEDS       = 40   # hard cap across ALL categories per refresh
MAX_FEEDS_PER_CATEGORY= 4    # cap per category per refresh
MAX_ITEMS_PER_FEED    = 60   # story cap per feed
PER_REQUEST_TIMEOUT   = 5    # seconds
DISK_CACHE_TTL_SEC    = 600  # 10 minutes
DISK_CACHE_DIR        = "data"
DISK_CACHE_PATH       = os.path.join(DISK_CACHE_DIR, "news_cache.json")

# ---- Time parsing (tz-safe to UTC) ----
from dateutil import parser as dtparser
from datetime import datetime, timezone, timedelta

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

# ---- Disk cache helpers ----
def _cache_write(df: pd.DataFrame):
    try:
        os.makedirs(DISK_CACHE_DIR, exist_ok=True)
        payload = {
            "ts": time.time(),
            "rows": df.assign(published_dt=df["published_dt"].astype(str)).to_dict(orient="records")
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
        if df.empty:
            return None
        df["published_dt"] = pd.to_datetime(df["published_dt"], utc=True, errors="coerce").fillna(
            pd.Timestamp.utcnow().tz_localize("UTC")
        )
        return df.sort_values("published_dt", ascending=False).reset_index(drop=True)
    except Exception:
        return None

# ---- Fetchers ----
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
                # published
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

# ---- Main public API ----
def get_news_dataframe(catalog_path: str) -> pd.DataFrame:
    """
    Returns DataFrame with columns:
    category, source, title, link, summary, published_dt (UTC tz-aware)
    Uses disk cache (10 min). Caps total RSS hits to stay responsive on cold starts.
    """
    # Serve from disk cache if fresh
    cached = _cache_read()
    if cached is not None and not cached.empty:
        return cached

    # Load catalog
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception:
        catalog = {}

    # Build a capped list of feeds to hit this refresh
    planned: List[tuple[str, str]] = []  # (category, url)
    for category, urls in catalog.items():
        urls = list(urls)
        random.shuffle(urls)
        for u in urls[:MAX_FEEDS_PER_CATEGORY]:
            planned.append((category, u))
    random.shuffle(planned)
    planned = planned[:MAX_TOTAL_FEEDS]

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
        # If network completely fails, still return previous cache if any (even if stale)
        stale = _cache_read()
        return stale if stale is not None else df

    df["title"] = df["title"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df["summary"] = df["summary"].fillna("").astype(str)
    df["published_dt"] = pd.to_datetime(df["published_dt"], utc=True, errors="coerce").fillna(
        pd.Timestamp.utcnow().tz_localize("UTC")
    )
    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)

    # Write to disk cache for next cold start
    _cache_write(df)
    return df
