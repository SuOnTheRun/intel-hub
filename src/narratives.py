# src/narratives.py
# Strategist Playbook (ad-tech oriented, data-driven)

from collections import Counter
import re
import pandas as pd
import numpy as np

# very light stoplist for bigram extraction
_STOP = set("""
a an and are as at be by for from has have if in into is it its of on or our over
than that the their there this to via was were will with your you we us about after before
""".split())

def _bigrams_from_titles(df: pd.DataFrame, col: str = "title", top: int = 8):
    """Return top 'top' bigrams from news titles (quick and dependency-free)."""
    if df is None or df.empty or col not in df:
        return []
    def toks(s: str):
        words = re.findall(r"[A-Za-z][A-Za-z\-]+", (s or "").lower())
        return [w for w in words if w not in _STOP and len(w) > 2]
    c = Counter()
    for t in df[col].astype(str):
        ws = toks(t)
        for i in range(len(ws) - 1):
            w1, w2 = ws[i], ws[i+1]
            if w1 in _STOP or w2 in _STOP:
                continue
            c[f"{w1} {w2}"] += 1
    return [w for w, _ in c.most_common(top)]

def strategist_playbook(breakdown: dict, market_hist: pd.DataFrame,
                        tsa_df: pd.DataFrame, news_df: pd.DataFrame):
    """
    Build an ad-tech strategist’s short playbook from live signals.
    Returns: {"marketing": [...], "insight": [...], "topics": [...]}
    """
    comp = breakdown.get("components", {})
    out_mkt, out_ins, out_topics = [], [], []

    # --- Marketing posture (budget/flight/creative guardrails)
    if comp:
        if comp.get("vix", {}).get("risk", 0) >= 60:
            out_mkt.append("Keep budgets flexible; shorter flights & faster optimisation while VIX is elevated.")
        if comp.get("tone", {}).get("risk", 0) >= 60:
            out_mkt.append("Tighten brand-safety and context filters on hard-news inventory.")
        if comp.get("tsa", {}).get("risk", 0) >= 60:
            out_mkt.append("De-emphasise travel-moment creatives; lean into at-home/comparison shopping intents.")
        if comp.get("volume", {}).get("risk", 0) >= 60:
            out_mkt.append("Expect pricier premium news inventory (coverage surge); pre-book only if context aligns.")

    if market_hist is not None and not market_hist.empty:
        from .risk_model import market_momentum
        mom = market_momentum(market_hist)
        if mom.get("Nasdaq 100", 0) > 0 and mom.get("S&P 500", 0) > 0:
            out_mkt.append("Tech & broad-market momentum positive; test performance formats with tighter ROAS targets.")
        if mom.get("Nasdaq 100", 0) < 0:
            out_mkt.append("Tech momentum cooling; rotate creative to value/utility messages.")

    # --- Insight watchlist (what to track / expect)
    if comp.get("cisa", {}).get("risk", 0) >= 60:
        out_ins.append("Monitor CISA hourly for vendor/library CVEs affecting fintech/retail apps.")
    if comp.get("fema", {}).get("risk", 0) >= 60:
        out_ins.append("Overlay FEMA regions on retail campaigns to anticipate supply/footfall shocks.")
    if tsa_df is not None and not tsa_df.empty:
        latest = float(tsa_df["delta_vs_2019_pct"].dropna().iloc[-1])
        if latest < -5:
            out_ins.append(f"Travel intent trails 2019 by {latest:.1f}% — reduce airport-adjacent audience reliance.")
    out_ins.append(f"Tension Index {breakdown.get('index','—')} — weighted percentiles of Tone/Volume/CISA/FEMA/VIX/TSA.")

    # --- Emerging topics from headlines (top bigrams)
    topics = _bigrams_from_titles(news_df, "title", top=8)
    if topics:
        out_topics = [f"• {t}" for t in topics[:8]]

    return {"marketing": out_mkt, "insight": out_ins, "topics": out_topics}
