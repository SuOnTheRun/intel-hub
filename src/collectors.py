# src/collectors.py
from __future__ import annotations
import io, os, re, time, json, math, zipfile
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests
import requests_cache
import feedparser
import yfinance as yf

# A single shared cache for all HTTP calls (SQLite on disk).
requests_cache.install_cache(
    "intel_cache",
    backend="sqlite",
    expire_after=timedelta(minutes=15),  # sensible default; some sources override via .cache()
)

UTC = timezone.utc

# --------- UTILITIES

def _now():
    return datetime.now(UTC)

def _http_get(url: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "US-Intel-Hub/1.0 (+https://render.com)")
    r = requests.get(url, headers=headers, timeout=kwargs.pop("timeout", 30), **kwargs)
    r.raise_for_status()
    return r

def _to_dt(x):
    if isinstance(x, datetime):
        return x.astimezone(UTC)
    try:
        return datetime.fromisoformat(str(x).replace("Z","+00:00")).astimezone(UTC)
    except Exception:
        return None

# --------- GOOGLE NEWS RSS (no key)
def fetch_latest_news(region: str = "us", query: Optional[str] = None, limit: int = 25) -> pd.DataFrame:
    """
    Google News RSS. Region-aware feed.
    """
    base = f"https://news.google.com/rss?hl=en-{region.upper()}&gl={region.upper()}&ceid={region.upper()}:en"
    url = base if not query else base + "&q=" + requests.utils.quote(query)
    feed = feedparser.parse(url)
    rows = []
    for e in feed.entries[:limit]:
        rows.append({
            "time": _to_dt(getattr(e, "published", None)) or _now(),
            "source": getattr(getattr(e, "source", None), "title", "") or "GoogleNews",
            "title": e.title,
            "link": e.link
        })
    return pd.DataFrame(rows).sort_values("time", ascending=False).reset_index(drop=True)

# --------- GDELT GKG/Events (no key)
def _gdelt_day_url(day: datetime, kind: str) -> str:
    day_str = day.strftime("%Y%m%d")
    if kind == "gkg":
        return f"http://data.gdeltproject.org/gdeltv2/{day_str}.gkg.csv.zip"
    if kind == "events":
        return f"http://data.gdeltproject.org/events/{day_str}.export.CSV.zip"
    raise ValueError("kind must be gkg|events")

def fetch_gdelt_gkg_last_n_days(n_days: int = 2) -> pd.DataFrame:
    """
    Pull GDELT GKG for last n_days; returns columns: datetime, sourceurl, tone, themes, locations.
    """
    frames: List[pd.DataFrame] = []
    for i in range(n_days):
        day = _now() - timedelta(days=i)
        try:
            r = _http_get(_gdelt_day_url(day, "gkg"))
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                name = [n for n in zf.namelist() if n.endswith(".csv")][0]
                df = pd.read_csv(zf.open(name), sep="\t", header=None, dtype=str, quoting=3, on_bad_lines="skip")
                # Reference: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
                df = df[[1, 3, 7, 9, 13]].copy()
                df.columns = ["datetime", "sourceurl", "themes", "tone", "locations"]
                # tone column is a semicolon-delimited metrics; first value is Tone
                df["tone"] = df["tone"].astype(str).str.split(",").str[0].astype(float)
                df["datetime"] = pd.to_datetime(df["datetime"], format="%Y%m%d%H%M%S", utc=True, errors="coerce")
                frames.append(df)
        except Exception:
            continue
    if not frames:
        return pd.DataFrame(columns=["datetime","sourceurl","themes","tone","locations"])
    out = pd.concat(frames, ignore_index=True)
    # Filter items that appear to be US-related via location string or "US"/state names
    states = ("United States","U.S.","USA","US", "New York","California","Texas","Florida","Illinois","Washington","Virginia","Georgia","Ohio","Pennsylvania","Arizona","North Carolina","New Jersey","Michigan","Massachusetts","Maryland","Colorado","Tennessee","Indiana","Missouri","Minnesota","Wisconsin","Alabama","Oregon","South Carolina","Kentucky","Oklahoma","Connecticut","Iowa","Utah","Nevada","Arkansas","Mississippi","Kansas","New Mexico","Nebraska","Idaho","West Virginia","Hawaii","New Hampshire","Maine","Rhode Island","Montana","Delaware","South Dakota","North Dakota","Vermont","Wyoming","Alaska","District of Columbia")
    mask = out["locations"].fillna("").str.contains("|".join(map(re.escape, states)))
    return out.loc[mask].reset_index(drop=True)

# --------- TSA CHECKPOINT THROUGHPUT (no key)
def fetch_tsa_throughput() -> pd.DataFrame:
    """
    Official TSA CSV: https://www.tsa.gov/travel/passenger-volumes
    Provides date and throughput for 2019 and current years.
    """
    url = "https://www.tsa.gov/sites/default/files/tsacheckpointtravelnumbers.csv"
    r = _http_get(url)
    df = pd.read_csv(io.StringIO(r.text))
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    # keep last 180 days; compute 7d avg and baseline vs 2019
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date")
    today_year = df["date"].dt.year.max()
    cur = df.rename(columns={str(today_year): "current", "2019": "baseline_2019"})
    cur["current_7dma"] = cur["current"].rolling(7).mean()
    cur["baseline_7dma"] = cur["baseline_2019"].rolling(7).mean()
    cur["delta_vs_2019_pct"] = ((cur["current_7dma"] - cur["baseline_7dma"]) / cur["baseline_7dma"]) * 100
    return cur.tail(210).reset_index(drop=True)

# --------- MARKETS via yfinance (no key)
_TICKERS = {
    "S&P 500": "^GSPC",
    "Nasdaq 100": "^NDX",
    "VIX": "^VIX",
    "10Y": "^TNX",  # CBOE 10Y yield index (approx)
}

def fetch_market_snapshot() -> Tuple[Dict[str, float], pd.DataFrame]:
    data = {}
    hist_frames = []
    for name, t in _TICKERS.items():
        tk = yf.Ticker(t)
        try:
            price = float(tk.info.get("regularMarketPrice") or tk.fast_info.last_price)
        except Exception:
            price = np.nan
        data[name] = price
        h = tk.history(period="3mo", interval="1d")["Close"].rename(name)
        hist_frames.append(h)
    hist = pd.concat(hist_frames, axis=1)
    return data, hist

# --------- CISA Alerts RSS (no key)
def fetch_cisa_alerts(limit: int = 30) -> pd.DataFrame:
    url = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
    feed = feedparser.parse(url)
    rows = []
    for e in feed.entries[:limit]:
        rows.append({
            "time": _to_dt(getattr(e,"published",None)) or _now(),
            "title": e.title,
            "link": e.link,
        })
    return pd.DataFrame(rows).sort_values("time", ascending=False).reset_index(drop=True)

# --------- FEMA Disaster Declarations (no key)
def fetch_fema_disasters(limit: int = 50) -> pd.DataFrame:
    # OpenFEMA API
    url = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries?$orderby=declarationDate%20desc&$top=100"
    r = _http_get(url)
    js = r.json().get("DisasterDeclarationsSummaries", [])
    rows = []
    for x in js[:limit]:
        rows.append({
            "time": _to_dt(x.get("declarationDate")),
            "state": x.get("state"),
            "type": x.get("incidentType"),
            "title": f"{x.get('incidentType')} — {x.get('declarationTitle','')}".strip(),
            "link": f"https://www.fema.gov/disaster/{x.get('disasterNumber')}"
        })
    return pd.DataFrame(rows).dropna(subset=["time"]).sort_values("time", ascending=False).reset_index(drop=True)
