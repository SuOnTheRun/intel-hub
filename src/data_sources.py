"""
data_sources.py

Data source registry + category market/trend signals for the Intelligence Hub.

- Loads feed catalogs from repo JSON files.
- Category-level Google Trends momentum via pytrends.
- Category-level market % change (5–7 trading days) via yfinance.

Categories are broad, defensible, and stable over time.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf
from pytrends.request import TrendReq

ROOT = Path(__file__).resolve().parents[1]

# -----------------------------
# JSON loaders (kept from the earlier app)
# -----------------------------
def _load_json(name: str):
    p = ROOT / name
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def news_catalog() -> Dict[str, List[str]]:
    return _load_json("news_rss_catalog.json")

def gov_catalog() -> Dict[str, List[str]]:
    return _load_json("gov_regulatory_feeds.json")

def geo_cyber_catalog() -> Dict[str, List[str]]:
    return _load_json("geo_cyber_event_feeds.json")

def incident_catalog() -> Dict[str, str]:
    return _load_json("incident_sources.json")

def social_catalog() -> Dict[str, List[str]]:
    return _load_json("social_sources.json")


# -----------------------------
# Google Trends client
# IST offset (330) keeps parity with your prior UI defaults; geo left blank for global & US queries in payload.
# -----------------------------
_pytrends = TrendReq(hl="en-US", tz=330)

# -----------------------------
# Category → Google Trends terms
# Keep these high-signal and generic so they work globally and over time.
# -----------------------------
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "Consumer Staples": ["FMCG", "consumer staples", "packaged food", "household products"],
    "Energy": ["oil", "natural gas", "OPEC", "renewable energy", "LNG"],
    "Technology": ["artificial intelligence", "semiconductor", "data center", "cloud computing", "cybersecurity"],
    "Automotive": ["electric vehicle", "battery", "autonomous car", "automotive industry"],
    "Financials": ["banking", "fintech", "payments", "nbfc", "insurance"],
    "Media & Advertising": ["advertising", "adtech", "programmatic", "CTV", "retail media"],
    "Healthcare": ["pharma", "biotech", "clinical trial", "vaccine", "healthcare"],
    "Telecom": ["5G", "mobile network", "fiber broadband", "telecommunications"],
    "Retail & E-commerce": ["ecommerce", "retail", "consumer spending", "marketplace"],
    "Defense & Security": ["defense", "military", "geopolitics", "national security"],
    "Real Estate": ["real estate", "housing market", "REIT", "construction"],
    "Metals & Mining": ["copper", "steel", "aluminium", "mining"],
    "Agriculture": ["agriculture", "fertilizer", "crop output", "monsoon"],
    "Climate & ESG": ["climate change", "ESG", "sustainability", "carbon emissions", "net zero"]
}

# -----------------------------
# Category → liquid market proxies (ETFs / futures / large-caps / indices)
# We average their recent % change as the category market signal.
# -----------------------------
CATEGORY_TICKERS: Dict[str, List[str]] = {
    "Consumer Staples": ["XLP", "PG", "UL"],
    "Energy": ["XLE", "CL=F", "NG=F", "XOM", "BP"],
    "Technology": ["XLK", "SMH", "NVDA", "AAPL", "^NDX"],
    "Automotive": ["TSLA", "F", "GM", "RIVN"],
    "Financials": ["XLF", "JPM", "BAC", "^NSEBANK"],
    "Media & Advertising": ["GOOGL", "META", "TTD", "ROKU"],
    "Healthcare": ["XLV", "JNJ", "UNH", "PFE"],
    "Telecom": ["IYZ", "TMUS", "VZ", "T"],
    "Retail & E-commerce": ["XRT", "AMZN", "BABA", "SHOP"],
    "Defense & Security": ["ITA", "LMT", "RTX", "NOC"],
    "Real Estate": ["VNQ", "SPG", "XHB"],
    "Metals & Mining": ["XME", "BHP", "RIO", "GLEN.L"],
    "Agriculture": ["DBA", "MOS", "NTR"],
    "Climate & ESG": ["ICLN", "ENPH", "FSLR", "PLUG"]
}

# -----------------------------
# Helpers
# -----------------------------
def _safe_mean(values: List[float]) -> float:
    vs = [float(v) for v in values if pd.notna(v)]
    return float(np.mean(vs)) if vs else 0.0

def get_trends_score(keyword_list: List[str], lookback_days: int = 7, geo: str = "US") -> float:
    """
    Single momentum score for a list of keywords:
    mean Google Trends interest over the past lookback_days.
    """
    try:
        kw = keyword_list[:5] if len(keyword_list) > 5 else keyword_list
        if not kw:
            return 0.0
        _pytrends.build_payload(kw_list=kw, timeframe=f"now {lookback_days}-d", geo=geo or "")
        df = _pytrends.interest_over_time()
        if df is None or df.empty:
            return 0.0
        cols = [c for c in df.columns if c != "isPartial"]
        if not cols:
            return 0.0
        return float(df[cols].mean(axis=1).mean())
    except Exception:
        return 0.0

def get_market_change(symbols: List[str], lookback_days: int = 7) -> float:
    """
    Average % change across tickers over ~lookback_days.
    """
    if not symbols:
        return 0.0
    try:
        end = datetime.now(timezone.utc)
        start = end - relativedelta(days=lookback_days)
        data = yf.download(
            symbols,
            start=start.date(),
            end=end.date(),
            progress=False,
            group_by="ticker",
            auto_adjust=True,
            threads=True,
        )
        pct_changes: List[float] = []
        if isinstance(data.columns, pd.MultiIndex):
            for s in symbols:
                try:
                    if s not in data.columns.get_level_values(0):
                        continue
                    series = data[s]["Close"].dropna()
                    if len(series) >= 2 and series.iloc[0] != 0:
                        pct = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100.0
                        pct_changes.append(float(pct))
                except Exception:
                    continue
        else:
            series = data.get("Close", pd.Series(dtype=float)).dropna()
            if len(series) >= 2 and series.iloc[0] != 0:
                pct = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100.0
                pct_changes.append(float(pct))
        return _safe_mean(pct_changes)
    except Exception:
        return 0.0

# -----------------------------
# Public API (used by analytics/UI)
# -----------------------------
def category_market_trends(lookback_days: int = 7, geo: str = "US") -> pd.DataFrame:
    """
    Returns per-category signals:
      - trends: Google Trends momentum (0–100 scale, averaged across terms)
      - market_pct: average recent percent change across mapped tickers
    Columns: [category, trends, market_pct]
    """
    rows = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        try:
            trends = get_trends_score(kws, lookback_days=lookback_days, geo=geo)
        except Exception:
            trends = 0.0
        tickers = CATEGORY_TICKERS.get(cat, [])
        try:
            market = get_market_change(tickers, lookback_days=lookback_days)
        except Exception:
            market = 0.0
        rows.append({"category": cat, "trends": float(trends), "market_pct": float(market)})
    df = pd.DataFrame(rows)
    return df.sort_values("category").reset_index(drop=True)
