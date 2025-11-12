# src/narratives.py
from __future__ import annotations
from typing import Dict, List
import pandas as pd
from .analytics import summarize_headlines

TENSION_BANDS = [(0,30,"Low"),(30,50,"Guarded"),(50,70,"Elevated"),(70,85,"High"),(85,101,"Severe")]

def _band_name(score: float) -> str:
    for lo, hi, name in TENSION_BANDS:
        if lo <= score < hi:
            return name
    return "Unknown"

def strategic_brief(tension: float, news_df: pd.DataFrame) -> Dict[str, List[str] | str]:
    """
    Generates a short, operationally useful brief from inputs.
    """
    band = _band_name(tension)
    bullets = []
    headlines_summary = summarize_headlines(news_df, n=6)

    # Core situation
    bullets.append(f"National Tension Index is **{tension:.1f}** ({band}).")
    if headlines_summary["negative"]:
        bullets.append(f"Negative pressure from: { '; '.join(headlines_summary['negative'][:3]) }.")
    if headlines_summary["positive"]:
        bullets.append(f"Offsetting positives: { '; '.join(headlines_summary['positive'][:2]) }.")

    # Watchlist rules of thumb
    next_steps = []
    if tension >= 70:
        next_steps += [
            "Increase cadence of monitoring to hourly on cyber and market stress.",
            "Prepare contingency messaging for supply-chain or operational disruptions.",
            "Tighten campaign flighting controls; prefer flexible budgets and rapid creative swaps."
        ]
    elif tension >= 50:
        next_steps += [
            "Activate daily checks for CISA advisories and FEMA declarations.",
            "Review category exposure (Finance/Travel/Retail) for message sensitivity.",
            "Track VIX and TSA momentum for coupled market–mobility signals."
        ]
    else:
        next_steps += [
            "Maintain standard daily monitoring; log notable regulatory items.",
            "Explore opportunistic placements in sectors showing positive momentum."
        ]

    return {
        "summary": "\n\n".join(bullets),
        "headlines": headlines_summary,
        "next_steps": next_steps
    }

# --- Strategist Playbook (ad-tech oriented, no placeholders) ---
from collections import Counter
import re
import pandas as pd
import numpy as np

_STOP = set("""
a an and are as at be by for from has have if in into is it its of on or our over
than that the their there this to via was were will with your you we us about after before
""".split())

def _bigrams_from_titles(df: pd.DataFrame, col: str = "title", top: int = 8):
    if df is None or df.empty or col not in df: 
        return []
    def toks(s: str):
        words = re.findall(r"[A-Za-z][A-Za-z\-]+", (s or "").lower())
        return [w for w in words if w not in _STOP and len(w) > 2]
    c = Counter()
    for t in df[col].astype(str).tolist():
        ws = toks(t)
        for i in range(len(ws)-1):
            bg = f"{ws[i]} {ws[i+1]}"
            if any(x in _STOP for x in ws[i:i+2]): 
                continue
            c[bg] += 1
    return [w for w,_ in c.most_common(top)]

def strategist_playbook(breakdown: dict, market_hist: pd.DataFrame, tsa_df: pd.DataFrame, news_df: pd.DataFrame):
    """
    Returns dict with three lists: marketing, insight, topics.
    All bullets are driven by live inputs; no fake content.
    """
    comp = breakdown.get("components", {})
    out_mkt, out_ins, out_topics = [], [], []

    # --- Marketing posture (budget/flight/creative guardrails)
    if comp:
        if comp["vix"]["risk"] >= 60:
            out_mkt.append("Keep budgets flexible; prefer shorter flights and faster optimisation cycles while VIX is elevated.")
        if comp["tone"]["risk"] >= 60:
            out_mkt.append("Stress-test brand safety lists; tighten keyword/context filters on hard-news inventory.")
        if comp["tsa"]["risk"] >= 60:
            out_mkt.append("Shift away from travel-moment creatives; redirect to at-home/comparison shopping intents.")
        if comp["volume"]["risk"] >= 60:
            out_mkt.append("Expect costlier premium news inventory (coverage surge); pre-book only if contextually aligned.")
    if market_hist is not None and not market_hist.empty:
        # Momentum signals (20-day)
        from .risk_model import market_momentum
        mom = market_momentum(market_hist)
        if mom.get("Nasdaq 100",0) > 0 and mom.get("S&P 500",0) > 0:
            out_mkt.append("Tech & broad-market momentum positive; test performance formats with stronger ROAS targets.")
        if mom.get("Nasdaq 100",0) < 0:
            out_mkt.append("Tech momentum cooling; rotate creative to value/utility messages rather than hype.")

    # --- Insight watchlist (what to track / expect)
    if comp.get("cisa",{}).get("risk",0) >= 60:
        out_ins.append("Monitor CISA hourly for new advisories; note vendor/library CVEs affecting fintech and retail apps.")
    if comp.get("fema",{}).get("risk",0) >= 60:
        out_ins.append("Track FEMA & NOAA regions for supply/footfall shocks; overlay affected states on retail campaigns.")
    if tsa_df is not None and not tsa_df.empty:
        latest = float(tsa_df["delta_vs_2019_pct"].dropna().iloc[-1])
        if latest < -5:
            out_ins.append(f"Travel intent lagging 2019 by {latest:.1f}%; reduce reliance on airport-adjacent audiences.")
    # Always include index reading
    out_ins.append(f"Tension Index {breakdown.get('index','—')} — weighted percentile blend of tone, volume, CISA, FEMA, VIX, TSA.")

    # --- Emerging topics from headlines (top bigrams)
    topics = _bigrams_from_titles(news_df, "title", top=8)
    if topics:
        out_topics = [f"• {t}" for t in topics[:8]]

    return {"marketing": out_mkt, "insight": out_ins, "topics": out_topics}
