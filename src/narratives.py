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
