import asyncio
import aiohttp
import feedparser
import pandas as pd
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from typing import List, Dict

from .data_sources import news_catalog, gov_catalog, social_catalog
from .store import ttl_cache

UTC = timezone.utc

def _normalize_items(feed_url: str, fp):
    records = []
    for e in fp.entries:
        title = getattr(e, "title", "") or ""
        link  = getattr(e, "link", "") or ""
        published = getattr(e, "published", getattr(e, "updated", ""))
        summary = BeautifulSoup(getattr(e, "summary", ""), "lxml").text
        records.append({"source": feed_url, "title": title, "link": link, "published": published, "summary": summary})
    return records

async def _fetch_feed(session, url: str):
    async with session.get(url, timeout=20) as r:
        content = await r.read()
        fp = feedparser.parse(content)
        return _normalize_items(url, fp)

async def _gather(feeds: List[str]):
    async with aiohttp.ClientSession() as session:
        tasks = [_fetch_feed(session, u) for u in feeds]
        out = await asyncio.gather(*tasks, return_exceptions=True)
        rows = []
        for o in out:
            if isinstance(o, Exception):
                continue
            rows.extend(o)
        return pd.DataFrame(rows)

def _within(df: pd.DataFrame, days: int):
    def to_dt(x):
        try:
            return pd.to_datetime(x, utc=True)
        except Exception:
            return pd.NaT
    df = df.copy()
    df["published_dt"] = df["published"].apply(to_dt)
    cutoff = pd.Timestamp.utcnow() - pd.Timedelta(days=days)
    return df[df["published_dt"] >= cutoff].sort_values("published_dt", ascending=False).reset_index(drop=True)

class NewsCollector:
    @ttl_cache(ttl_seconds=900)
    def collect(self, categories: List[str], max_items: int = 100, lookback_days: int = 3) -> pd.DataFrame:
        catalog = news_catalog()
        feeds = []
        for c in categories:
            feeds.extend(catalog.get(c, []))
        feeds = list(dict.fromkeys(feeds))  # dedupe
        df = asyncio.run(_gather(feeds))
        df = _within(df, lookback_days)
        return df.head(max_items * len(categories))

class GovCollector:
    @ttl_cache(ttl_seconds=900)
    def collect(self, max_items: int = 200, lookback_days: int = 7) -> pd.DataFrame:
        feeds = sum(gov_catalog().values(), [])
        df = asyncio.run(_gather(feeds))
        df = _within(df, lookback_days)
        return df.head(max_items)

class SocialCollector:
    @ttl_cache(ttl_seconds=900)
    def collect(self, categories: List[str], max_items: int = 120, lookback_days: int = 3) -> pd.DataFrame:
        cat = social_catalog()
        feeds = []
        for c in categories:
            feeds.extend(cat.get(c, []))
        df = asyncio.run(_gather(list(set(feeds))))
        df = _within(df, lookback_days)
        return df.head(max_items)

class MacroCollector:
    @ttl_cache(ttl_seconds=900)
    def collect(self, lookback_days: int = 7) -> pd.DataFrame:
        # Macro via Google Trends interest for broad terms as a light, always-on signal
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        kw = ["inflation", "recession", "unemployment", "interest rates", "housing market"]
        pytrends.build_payload(kw_list=kw, timeframe="now 7-d", geo="US")
        df = pytrends.interest_over_time().reset_index().rename(columns={"date":"timestamp"})
        return df

class TrendsCollector:
    @ttl_cache(ttl_seconds=900)
    def collect(self, categories: List[str], lookback_days: int = 30) -> pd.DataFrame:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360)
        cat2kw = {
            "Technology": ["AI", "semiconductor", "cloud computing", "cybersecurity"],
            "Consumer": ["consumer spending", "loyalty program", "subscription", "discount"],
            "Energy": ["oil price", "gasoline price", "renewable energy"],
            "Healthcare": ["drug approval", "FDA recall", "telemedicine"],
            "Finance": ["bank earnings", "credit card delinquency", "ETF"],
            "Retail": ["foot traffic", "omnichannel", "same-day delivery"],
            "Autos": ["EV sales", "hybrid car", "dealer inventory"],
            "Macro": ["inflation", "interest rates", "housing market"],
        }
        kw = []
        for c in categories:
            kw += cat2kw.get(c, [])
        kw = list(dict.fromkeys(kw))[:5] or ["macro"]
        pytrends.build_payload(kw_list=kw, timeframe=f"now {lookback_days}-d", geo="US")
        df = pytrends.interest_over_time().reset_index().rename(columns={"date":"timestamp"})
        df["category"] = " / ".join(categories)
        return df

class MobilityCollector:
    @ttl_cache(ttl_seconds=1800)
    def collect(self) -> pd.DataFrame:
        # TSA checkpoint throughput: official daily table
        url = "https://www.tsa.gov/sites/default/files/tsa_travel_numbers.csv"
        df = pd.read_csv(url)
        df = df.rename(columns={"Date":"date", "Total Traveler Throughput":"throughput"}).dropna()
        df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date", ascending=False).head(30).reset_index(drop=True)

class StocksCollector:
    @ttl_cache(ttl_seconds=300)
    def collect(self, tickers: List[str]) -> pd.DataFrame:
        import yfinance as yf
        frames = []
        for t in tickers:
            try:
                info = yf.Ticker(t).history(period="5d")[-1:]
                if not info.empty:
                    last = info.iloc[0]
                    frames.append({
                        "ticker": t,
                        "price": float(last["Close"]),
                        "change": float(last["Close"] - last["Open"]),
                        "pct": float((last["Close"] - last["Open"]) / last["Open"] * 100.0),
                        "volume": int(last["Volume"]),
                    })
            except Exception:
                continue
        return pd.DataFrame(frames).sort_values("pct", ascending=False).reset_index(drop=True)
