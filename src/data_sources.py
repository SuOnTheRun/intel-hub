"""
data_sources.py

Category-level market & trends signals for the Intelligence Hub.

- Google Trends momentum (past 7 days) via pytrends
- Market % change (past ~5 trading days) via yfinance
- Categories aligned 1:1 with news_rss_catalog.json:
  Consumer Staples, Energy, Technology, Automotive, Financials,
  Media & Advertising, Healthcare, Telecom, Retail & E-commerce,
  Defense & Security, Real Estate, Metals & Mining, Agriculture, Climate & ESG
"""

from __future__ import annotations

import pandas as pd
import numpy as np
import yfinance as yf
from pytrends.request import TrendReq
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# --- Google Trends client (IST tz offset 330 minutes keeps parity with your UI) ---
pytrends = TrendReq(hl="en-US", tz=330)


# -----------------------------
# Category → Google Trends terms
# Keep these high-signal and generic so they work globally and over time.
# -----------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
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
# Choose instruments that are broadly available via Yahoo Finance.
# We average their 5-day % change as the category market signal.
# -----------------------------
CATEGORY_TICKERS: dict[str, list[str]] = {
    # Consumer staples: U.S. staples ETF + global mega-caps
    "Consumer Staples": ["XLP", "PG", "UL"],
    # Energy: sector ETF + crude & natgas futures + oil majors
    "Energy": ["XLE", "CL=F", "NG=F", "XOM", "BP"],
    # Technology: sector ETF + chips & mega-cap tech
    "Technology": ["XLK", "SMH", "NVDA", "AAPL", "^NDX"],
    # Automotive: EV + legacy autos
    "Automotive": ["TSLA", "F", "GM", "RIVN"],
    # Financials: sector ETF + money center banks + India bank index
    "Financials": ["XLF", "JPM", "BAC", "^NSEBANK"],
    # Media & Advertising: ad platforms + CTV + trade-desk proxy
    "Media & Advertising": ["GOOGL", "META", "TTD", "ROKU"],
    # Healthcare: sector ETF + diversified healthcare bellwethers
    "Healthcare": ["XLV", "JNJ", "UNH", "PFE"],
    # Telecom: telecom ETF + U.S. telcos (T-Mobile aligns with Blis ownership)
    "Telecom": ["IYZ", "TMUS", "VZ", "T"],
    # Retail & E-commerce: retail ETF + leaders across regions
    "Retail & E-commerce": ["XRT", "AMZN", "BABA", "SHOP"],
    # Defense & Security: aerospace & defense ETF + primes
    "Defense & Security": ["ITA", "LMT", "RTX", "NOC"],
    # Real Estate: REIT ETF + a flagship REIT + homebuilder proxy
    "Real Estate": ["VNQ", "SPG", "XHB"],
    # Metals & Mining: metals & mining ETF + global miners
    "Metals & Mining": ["XME", "BHP", "RIO", "GLEN.L"],
    # Agriculture: ag ETF + fertilizer majors
    "Agriculture": ["DBA", "MOS", "NTR"],
    # Climate & ESG: clean energy ETF + leading solar names
    "Climate & ESG": ["ICLN", "ENPH", "FSLR", "PLUG"]
}


# -----------------------------
# Helpers
# -----------------------------
def _safe_mean(values: list[float]) -> float:
    vs = [float(v) for v in values if pd.notna(v)]
    return float(np.mean(vs)) if len(vs) else 0.0


def get_trends_score(keyword_list: list[str]) -> float:
    """
    Returns a single momentum score for a list of keywords by taking the mean
    Google Trends interest over the past 7 days across those terms.
    Robust to API hiccups; returns 0.0 on failure.
    """
    try:
        kw = keyword_list[:5] if len(keyword_list) > 5 else keyword_list
        if not kw:
            return 0.0
        pytrends.build_payload(kw, timeframe="now 7-d", geo="")
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            return 0.0
        # Drop "isPartial" if present, average across terms then time.
        cols = [c for c in df.columns if c != "isPartial"]
        if not cols:
            return 0.0
        return float(df[cols].mean(axis=1).mean())
    except Exception:
        return 0.0


def get_market_change(symbols: list[str], lookback_days: int = 7) -> float:
    """
    Downloads recent prices for a list of tickers and returns the average %
    change from the first to the last available close within ~lookback_days.
    Uses auto_adjust=True to handle splits/dividends.
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
        pct_changes: list[float] = []

        # yfinance returns either a simple DataFrame (single ticker) or a MultiIndex
        if isinstance(data.columns, pd.MultiIndex):
            # Multi-ticker
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
            # Single-ticker or yfinance flattened structure
            series = data.get("Close", pd.Series(dtype=float)).dropna()
            if len(series) >= 2 and series.iloc[0] != 0:
                pct = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100.0
                pct_changes.append(float(pct))

        return _safe_mean(pct_changes)
    except Exception:
        return 0.0


# -----------------------------
# Public API
# -----------------------------
def category_metrics() -> pd.DataFrame:
    """
    Computes per-category signals:
      - trends: Google Trends momentum (0–100 scale, averaged across terms)
      - market_pct: average 5–7 day percent change across mapped tickers
    Returns a DataFrame with columns: [category, trends, market_pct]
    """
    rows = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        try:
            trends = get_trends_score(kws)
        except Exception:
            trends = 0.0

        tickers = CATEGORY_TICKERS.get(cat, [])
        try:
            market = get_market_change(tickers, lookback_days=7)
        except Exception:
            market = 0.0

        rows.append(
            {
                "category": cat,
                "trends": float(trends),
                "market_pct": float(market),
            }
        )

    df = pd.DataFrame(rows)
    # Ensure stable category ordering for readability
    if not df.empty:
        df = df.sort_values("category").reset_index(drop=True)
    return df


# ------------------------------
# DATA ROUTERS FOR US
# ------------------------------
from .collectors import (
    collect_us_google_news,
    collect_us_gdelt_events,
    collect_us_trends,
    collect_us_fred
)
from .analytics import score_text_sentiment

def load_us_news() -> pd.DataFrame:
    df = collect_us_google_news(categories=["retail", "qsr", "consumer", "smartphone", "auto car"])
    df = score_text_sentiment(df, text_col="title")
    return df

def load_us_incidents() -> pd.DataFrame:
    return collect_us_gdelt_events(hours_back=48)

def load_us_trends() -> pd.DataFrame:
    return collect_us_trends(days=90)

def load_us_macro() -> pd.DataFrame:
    return collect_us_fred()
