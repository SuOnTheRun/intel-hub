# src/alerts.py — Alert collection (cached, capped, defensive)

from __future__ import annotations
import json, time, random
from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd

# Prefer feedparser, but keep a tiny XML fallback
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None
import urllib.request
import xml.etree.ElementTree as ET

# ---- Tunables for free hosting ----
PER_REQUEST_TIMEOUT = 5        # seconds hard timeout per RSS call
MAX_RSS_SOURCES     = 18       # total external RSS sources per refresh (policy+geo+cyber combined)
MAX_ITEMS_PER_FEED  = 3        # items to read from each feed

@dataclass
class Alert:
    kind: str            # "data", "policy", "geo", "cyber", "humint"
    title: str           # source/category
    detail: str          # one-line summary
    link: Optional[str]  # external link if any
    ts: float            # epoch seconds
    severity: int        # 1–5

def _now() -> float:
    return time.time()

def _safe_read_json(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ----------- RSS helpers -----------
def _pull_feed(url: str, max_items: int = MAX_ITEMS_PER_FEED, timeout_s: int = PER_REQUEST_TIMEOUT) -> List[Dict]:
    """
    Pull RSS/Atom items with strict timeouts; returns [{'title','link','published_ts'}].
    """
    out: List[Dict] = []
    try:
        if feedparser:
            d = feedparser.parse(url, request_headers={"User-Agent": "intel-hub/1.0"})
            for e in d.entries[:max_items]:
                ts = 0.0
                if getattr(e, "published_parsed", None):
                    try:
                        ts = time.mktime(e.published_parsed)
                    except Exception:
                        ts = _now()
                out.append({
                    "title": getattr(e, "title", "Untitled"),
                    "link": getattr(e, "link", None),
                    "published_ts": ts or _now()
                })
            return out

        # fallback: minimal XML with timeout
        req = urllib.request.Request(url, headers={"User-Agent": "intel-hub/1.0"})
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            data = r.read()
        root = ET.fromstring(data)
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for it in items[:max_items]:
            title = (it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "Untitled").strip()
            link_node = it.find("link") or it.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.text if (link_node is not None and link_node.text) else (link_node.get("href") if link_node is not None else None)
            out.append({"title": title, "link": link, "published_ts": _now()})
    except Exception:
        # swallow timeouts/network errors
        pass
    return out

# ----------- Data-driven alerts (no network) -----------
def collect_data_alerts(heat_df: pd.DataFrame, news_df: pd.DataFrame, tension_df: pd.DataFrame) -> List[Alert]:
    alerts: List[Alert] = []
    if heat_df is None or heat_df.empty:
        return alerts

    tens_map = {}
    if tension_df is not None and not tension_df.empty and "category" in tension_df:
        for _, r in tension_df.iterrows():
            try:
                tens_map[str(r["category"])] = float(r.get("tension_0_100", 0.0))
            except Exception:
                pass

    for _, r in heat_df.iterrows():
        cat = str(r["category"])
        news_z = float(r.get("news_z", 0.0))
        tone   = float(r.get("sentiment", 0.0))
        mkt    = float(r.get("market_pct", 0.0))
        trend  = float(r.get("trends", 0.0))
        tens   = tens_map.get(cat, 0.0)

        if news_z >= 1.5:
            alerts.append(Alert("data", cat, f"Elevated news momentum (z={news_z:.2f})", None, _now(), 3))
        if tone <= -0.30:
            alerts.append(Alert("data", cat, f"Adverse tone ({tone:.2f})", None, _now(), 4))
        if abs(mkt) >= 2.0:
            direction = "up" if mkt > 0 else "down"
            alerts.append(Alert("data", cat, f"Market moved {direction} {mkt:.2f}%", None, _now(), 3))
        if trend >= 70:
            alerts.append(Alert("data", cat, f"Public interest spiking (Trends {trend:.0f})", None, _now(), 2))
        if tens >= 60:
            alerts.append(Alert("data", cat, f"Heightened tension ({tens:.0f})", None, _now(), 4))

    alerts.sort(key=lambda a: (a.severity, a.ts), reverse=True)
    return alerts

# ----------- External alerts (capped) -----------
def _pick_sources(d: Dict[str, str], remaining: int) -> List[tuple]:
    items = list(d.items())
    random.shuffle(items)  # vary across refreshes
    return items[:max(0, remaining)]

def collect_policy_geo_cyber(catalog_path: str) -> List[Alert]:
    cfg = _safe_read_json(catalog_path)
    alerts: List[Alert] = []

    remaining = MAX_RSS_SOURCES

    # Policy/Regulators
    for name, url in _pick_sources(cfg.get("Policy_and_Regulators", {}), remaining):
        for it in _pull_feed(url):
            alerts.append(Alert("policy", name.replace("_", " "), it["title"], it.get("link"), it.get("published_ts", _now()), 3))
        remaining -= 1
        if remaining <= 0: break

    # Geo/Disaster
    if remaining > 0:
        for name, url in _pick_sources(cfg.get("Geo_Disaster", {}), remaining):
            for it in _pull_feed(url):
                sev = 4 if "USGS" in name or "GDACS" in name else 3
                alerts.append(Alert("geo", name.replace("_", " "), it["title"], it.get("link"), it.get("published_ts", _now()), sev))
            remaining -= 1
            if remaining <= 0: break

    # Cyber
    if remaining > 0:
        for name, url in _pick_sources(cfg.get("Cybersecurity", {}), remaining):
            for it in _pull_feed(url):
                sev = 4 if "CISA" in name else 3
                alerts.append(Alert("cyber", name.replace("_", " "), it["title"], it.get("link"), it.get("published_ts", _now()), sev))
            remaining -= 1
            if remaining <= 0: break

    alerts.sort(key=lambda a: (a.severity, a.ts), reverse=True)
    return alerts
