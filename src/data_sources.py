import pandas as pd, numpy as np, time
from pytrends.request import TrendReq
import yfinance as yf
from dateutil.relativedelta import relativedelta
from datetime import datetime, timezone

pytrends = TrendReq(hl="en-US", tz=330)

CATEGORY_KEYWORDS = {
    "Consumer Staples": ["FMCG", "consumer staples"],
    "Energy": ["oil", "gas", "OPEC"],
    "Technology": ["semiconductor", "cloud computing", "AI"],
    "Automotive": ["EV", "automotive"],
    "Financials": ["banking", "fintech"],
    "Media & Advertising": ["advertising", "adtech"],
    "Healthcare": ["pharma", "healthcare"]
}

CATEGORY_TICKERS = {
    "Consumer Staples": ["PG", "^NSEI"],
    "Energy": ["XOM","CL=F"],
    "Technology": ["NVDA","SMH"],
    "Automotive": ["TSLA","F"],
    "Financials": ["JPM","^NSEBANK"],
    "Media & Advertising": ["GOOGL","META"],
    "Healthcare": ["JNJ","PFE"]
}

def get_trends_score(keyword_list: list[str]) -> float:
    try:
        kw = keyword_list[:5]
        pytrends.build_payload(kw, timeframe="now 7-d", geo="")
        df = pytrends.interest_over_time()
        if df.empty:
            return 0.0
        return float(df[kw].mean().mean())
    except Exception:
        return 0.0

def get_market_change(symbols: list[str]) -> float:
    try:
        end = datetime.now(timezone.utc)
        start = end - relativedelta(days=5)
        data = yf.download(symbols, start=start.date(), end=end.date(), progress=False, group_by="ticker", auto_adjust=True, threads=True)
        changes = []
        for s in symbols:
            try:
                series = data[s]["Close"] if isinstance(data.columns, pd.MultiIndex) else data["Close"]
                if len(series) >= 2:
                    changes.append((series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100.0)
            except Exception:
                continue
        if not changes:
            return 0.0
        return float(np.mean(changes))
    except Exception:
        return 0.0

def category_metrics():
    rows = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        trends = get_trends_score(kws)
        market = get_market_change(CATEGORY_TICKERS.get(cat, []))
        rows.append({"category": cat, "trends": trends, "market_pct": market})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    # z-score news volume will be added in analytics; here we just return trends & market
    return df
