# src/collectors.py — robust feed collection with safe timezone parsing
from __future__ import annotations
import os, json, time, urllib.request, re
from typing import Dict, List
from urllib.parse import urlparse
import pandas as pd

# Prefer feedparser (faster, more tolerant); fall back to tiny XML
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None
import xml.etree.ElementTree as ET

# ---- time parsing (map common tz abbreviations) ----
from dateutil import parser as dtparser
from datetime import datetime, timezone, timedelta

_TZINFOS = {
    # North America
    "UTC": 0, "GMT": 0,
    "EST": -5*3600, "EDT": -4*3600,
    "CST": -6*3600, "CDT": -5*3600,
    "MST": -7*3600, "MDT": -6*3600,
    "PST": -8*3600, "PDT": -7*3600,
    # Europe
    "BST": 1*3600,   # British Summer
    "WET": 0, "WEST": 1*3600,
    "CET": 1*3600, "CEST": 2*3600,
    "EET": 2*3600, "EEST": 3*3600,
    # India (IST)
    "IST": 19800,    # Asia/Kolkata (UTC+5:30)
    # Misc
    "JST": 9*3600, "KST": 9*3600, "HKT": 8*3600, "SGT": 8*3600, "AEST": 10*3600, "AEDT": 11*3600,
}

def _to_utc(ts_str: str) -> pd.Timestamp:
    """
    Parse many RSS date variants reliably; return UTC pandas Timestamp.
    Falls back to 'now' if parsing fails.
    """
    if not ts_str:
        return pd.Timestamp.utcnow().tz_localize("UTC")
    try:
        dt = dtparser.parse(ts_str, tzinfos={k: timedelta(seconds=v) for k, v in _TZINFOS.items()})
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return pd.Timestamp(dt.astimezone(timezone.utc))
    except Exception:
        return pd.Timestamp.utcnow().tz_localize("UTC")

def _fetch_feed(url: str, max_items: int = 60, timeout: int = 6) -> List[Dict]:
    """
    Return list of dicts: title, link, summary, published_dt (UTC), source.
    """
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
                    # feedparser also exposes published_parsed; use that if present
                    try:
                        t = time.mktime(getattr(e, "published_parsed"))
                        published = pd.Timestamp(t, unit="s", tz="UTC")
                    except Exception:
                        published = pd.Timestamp.utcnow().tz_localize("UTC")
                items.append({"title": title, "link": link, "summary": desc, "published_dt": published})
            return items

        # XML fallback
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

def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""

def get_news_dataframe(catalog_path: str) -> pd.DataFrame:
    """
    Reads src/news_rss_catalog.json and merges all categories into one DataFrame:
    columns: category, source, title, link, summary, published_dt
    """
    try:
        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except Exception:
        catalog = {}

    rows: List[Dict] = []
    for category, urls in catalog.items():
        for url in urls:
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
        return df

    # Clean and order
    df["title"] = df["title"].fillna("").astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
    df["summary"] = df["summary"].fillna("").astype(str)
    # Ensure UTC tz-aware
    try:
        df["published_dt"] = pd.to_datetime(df["published_dt"], utc=True, errors="coerce")
        df["published_dt"] = df["published_dt"].fillna(pd.Timestamp.utcnow().tz_localize("UTC"))
    except Exception:
        df["published_dt"] = pd.Timestamp.utcnow().tz_localize("UTC")

    df = df.sort_values("published_dt", ascending=False).reset_index(drop=True)
    return df
