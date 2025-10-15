# src/alerts.py — Alert collection for Command Center (light, defensive)

from __future__ import annotations
import json, time
from dataclasses import dataclass
from typing import List, Dict, Optional
import pandas as pd

# Try feedparser; fall back to a tiny XML reader if unavailable
try:
    import feedparser  # type: ignore
except Exception:
    feedparser = None
import urllib.request
import xml.etree.ElementTree as ET

@dataclass
class Alert:
    kind: str            # "data", "policy", "geo", "cyber", "humint"
    title: str           # short label shown on the ribbon
    detail: str          # one-line explanation
    link: Optional[str]  # external link if any
    ts: float            # epoch time for sorting
    severity: int        # 1–5 => visual weight

def _now() -> float:
    return time.time()

def _safe_read_json(path: str) -> Dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ----------- RSS helpers -----------
def _pull_feed(url: str, max_items: int = 5) -> List[Dict]:
    """
    Pull RSS/Atom items; returns list of {'title','link','published_ts'}.
    Tries feedparser; falls back to minimal XML parse.
    """
    out: List[Dict] = []
    try:
        if feedparser:
            d = feedparser.parse(url)
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
        # fallback
        with urllib.request.urlopen(url, timeout=8) as r:
            data = r.read()
        root = ET.fromstring(data)
        # support both RSS and Atom
        items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for it in items[:max_items]:
            title = (it.findtext("title") or it.findtext("{http://www.w3.org/2005/Atom}title") or "Untitled").strip()
            link_node = it.find("link") or it.find("{http://www.w3.org/2005/Atom}link")
            link = link_node.text if (link_node is not None and link_node.text) else (link_node.get("href") if link_node is not None else None)
            out.append({"title": title, "link": link, "published_ts": _now()})
    except Exception:
        pass
    return out

# ----------- Collectors -----------
def collect_policy_alerts(catalog_path: str, max_per_source: int = 3) -> List[Alert]:
    cfg = _safe_read_json(catalog_path).get("Policy_and_Regulators", {})
    alerts: List[Alert] = []
    for name, url in cfg.items():
        for it in _pull_feed(url, max_per_source):
            alerts.append(Alert(
                kind="policy",
                title=name.replace("_", " "),
                detail=it["title"],
                link=it.get("link"),
                ts=it.get("published_ts", _now()),
                severity=3
            ))
    return alerts

def collect_geo_cyber_alerts(catalog_path: str, max_per_source: int = 3) -> List[Alert]:
    cfg = _safe_read_json(catalog_path)
    alerts: List[Alert] = []

    for name, url in cfg.get("Geo_Disaster", {}).items():
        for it in _pull_feed(url, max_per_source):
            sev = 4 if "USGS" in name or "GDACS" in name else 3
            alerts.append(Alert(
                kind="geo",
                title=name.replace("_", " "),
                detail=it["title"],
                link=it.get("link"),
                ts=it.get("published_ts", _now()),
                severity=sev
            ))

    for name, url in cfg.get("Cybersecurity", {}).items():
        for it in _pull_feed(url, max_per_source):
            sev = 4 if "CISA" in name else 3
            alerts.append(Alert(
                kind="cyber",
                title=name.replace("_", " "),
                detail=it["title"],
                link=it.get("link"),
                ts=it.get("published_ts", _now()),
                severity=sev
            ))
    return alerts

# ----------- Data-driven alerts -----------
def collect_data_alerts(heat_df: pd.DataFrame, news_df: pd.DataFrame, tension_df: pd.DataFrame) -> List[Alert]:
    """
    Flag categories with unusual conditions. Thresholds are conservative to avoid noise.
    """
    alerts: List[Alert] = []
    if heat_df is None or heat_df.empty:
        return alerts

    # Map category → tension for joining
    tension_map = {}
    if tension_df is not None and not tension_df.empty and "category" in tension_df:
        for _, r in tension_df.iterrows():
            try:
                tension_map[str(r["category"])] = float(r.get("tension_0_100", 0.0))
            except Exception:
                pass

    for _, r in heat_df.iterrows():
        cat = str(r["category"])
        news_z = float(r.get("news_z", 0.0))
        tone = float(r.get("sentiment", 0.0))
        mkt = float(r.get("market_pct", 0.0))
        trend = float(r.get("trends", 0.0))
        tens = tension_map.get(cat, 0.0)

        # News spike
        if news_z >= 1.5:
            alerts.append(Alert("data", f"{cat}", f"Elevated news momentum (z={news_z:.2f})", None, _now(), 3))

        # Adverse tone
        if tone <= -0.30:
            alerts.append(Alert("data", f"{cat}", f"Adverse tone ({tone:.2f})", None, _now(), 3))

        # Market move
        if abs(mkt) >= 2.0:
            direction = "up" if mkt > 0 else "down"
            alerts.append(Alert("data", f"{cat}", f"Market moved {direction} {mkt:.2f}%", None, _now(), 3))

        # Public interest spike
        if trend >= 70:
            alerts.append(Alert("data", f"{cat}", f"Public interest spiking (Trends {trend:.0f})", None, _now(), 2))

        # High tension
        if tens >= 60:
            alerts.append(Alert("data", f"{cat}", f"Heightened tension ({tens:.0f})", None, _now(), 4))

    # Optional: negative extremes bubble higher
    for a in alerts:
        if "Adverse" in a.detail or "down" in a.detail or "tension" in a.detail:
            a.severity = max(a.severity, 4)

    return alerts

# ----------- Orchestrator -----------
def collect_all_alerts(
    incident_catalog_path: str,
    heat_df: pd.DataFrame,
    news_df: pd.DataFrame,
    tension_df: pd.DataFrame,
    rss_policy_geo: bool = True,
    limit_total: int = 24
) -> List[Alert]:
    alerts: List[Alert] = []
    try:
        alerts.extend(collect_data_alerts(heat_df, news_df, tension_df))
    except Exception:
        pass

    if rss_policy_geo:
        try:
            alerts.extend(collect_policy_alerts(incident_catalog_path))
        except Exception:
            pass
        try:
            alerts.extend(collect_geo_cyber_alerts(incident_catalog_path))
        except Exception:
            pass

    # Sort: severity desc, ts desc; then take top N
    alerts.sort(key=lambda a: (a.severity, a.ts), reverse=True)
    return alerts[:limit_total]
