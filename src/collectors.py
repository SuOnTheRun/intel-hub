import feedparser, pandas as pd, time, re
from datetime import datetime, timezone
from dateutil import parser as dtp
from pathlib import Path
import json
from diskcache import Cache

CACHE = Cache(directory=".cache_collectors", size_limit=2e9)  # ~2GB cap

def _norm_time(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    try:
        return dtp.parse(ts).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def load_catalog(catalog_path: str) -> dict:
    with open(catalog_path, "r") as f:
        return json.load(f)

@CACHE.memoize(expire=15*60)
def fetch_rss(url: str) -> list[dict]:
    # Avoid transient failures on free hosts
    fp = feedparser.parse(url)
    out = []
    for e in fp.entries[:30]:
        title = e.get("title", "").strip()
        link = e.get("link", "").strip()
        if not title or not link:
            continue
        published = e.get("published") or e.get("updated") or e.get("pubDate") or datetime.now(timezone.utc).isoformat()
        out.append({
            "title": title,
            "link": link,
            "published": _norm_time(published).isoformat(),
            "summary": re.sub(r"\s+", " ", e.get("summary", "")).strip(),
            "source": fp.feed.get("title", url)
        })
    return out

def get_news_dataframe(catalog_path: str) -> pd.DataFrame:
    cat = load_catalog(catalog_path)
    rows = []
    for category, urls in cat.items():
        for url in urls:
            try:
                items = fetch_rss(url)
                for it in items:
                    it["category"] = category
                    rows.append(it)
            except Exception:
                continue
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["category","title","link","published","summary","source"])
    df["published_dt"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    df = df.sort_values("published_dt", ascending=False).drop_duplicates(subset=["title"])
    return df.reset_index(drop=True)
