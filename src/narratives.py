# src/narratives.py
from __future__ import annotations
import re
import pandas as pd

# very compact keyword map → vertical
VERTICALS = {
    "healthcare": [
        r"flu|covid|measles|whooping cough|meningitis|dengue|hospital|cdc|drug shortage|vaccine|insulin|medicare"
    ],
    "travel": [
        r"tsa|airport|airline|flight|faa|weather alert|snowstorm|blizzard|hurricane|passport|visa"
    ],
    "retail": [
        r"black friday|cyber monday|shopper|mall|foot traffic|store closing|inventory|supply chain|discount|sale"
    ],
    "finance": [
        r"fed|interest rate|inflation|cpi|ppi|treasury|mortgage|bank|earnings|default|credit|housing market"
    ],
    "tech": [
        r"breach|outage|ransomware|vulnerability|cve|ai|chip|semiconductor|app store|privacy|antitrust"
    ],
    "auto": [
        r"ev|recall|dealer|fuel|gas price|auto sales|registration|highway|nhtsa"
    ],
}

US_STATES = {
    # simple state detector from headline text (name or postal)
    "AL":"alabama","AK":"alaska","AZ":"arizona","AR":"arkansas","CA":"california","CO":"colorado","CT":"connecticut",
    "DE":"delaware","FL":"florida","GA":"georgia","HI":"hawaii","ID":"idaho","IL":"illinois","IN":"indiana","IA":"iowa",
    "KS":"kansas","KY":"kentucky","LA":"louisiana","ME":"maine","MD":"maryland","MA":"massachusetts","MI":"michigan",
    "MN":"minnesota","MS":"mississippi","MO":"missouri","MT":"montana","NE":"nebraska","NV":"nevada","NH":"new hampshire",
    "NJ":"new jersey","NM":"new mexico","NY":"new york","NC":"north carolina","ND":"north dakota","OH":"ohio","OK":"oklahoma",
    "OR":"oregon","PA":"pennsylvania","RI":"rhode island","SC":"south carolina","SD":"south dakota","TN":"tennessee",
    "TX":"texas","UT":"utah","VT":"vermont","VA":"virginia","WA":"washington","WV":"west virginia","WI":"wisconsin","WY":"wyoming",
    "DC":"district of columbia"
}

def _match_any(text: str, patterns: list[str]) -> bool:
    t = text.lower()
    return any(re.search(p, t) for p in patterns)

def _states_from_title(title: str) -> list[str]:
    t = title.lower()
    hits = []
    for abbr, name in US_STATES.items():
        if re.search(rf"\b{abbr.lower()}\b", t) or re.search(rf"\b{name}\b", t):
            hits.append(abbr)
    return hits

def _top_topics_by_state(news_df: pd.DataFrame, top_k: int = 5) -> dict[str, list[str]]:
    if news_df is None or news_df.empty: return {}
    buckets: dict[str, dict[str,int]] = {}
    for _, r in news_df.iterrows():
        title = str(r.get("title",""))
        states = _states_from_title(title)
        if not states: continue
        # quick keyword tokens
        words = [w for w in re.findall(r"[a-zA-Z]{4,}", title.lower()) if w not in {"with","from","that","this","have","will"}]
        if not words: continue
        for st in states:
            buckets.setdefault(st, {})
            for w in words:
                buckets[st][w] = buckets[st].get(w, 0) + 1
    out = {}
    for st, bag in buckets.items():
        ranked = sorted(bag.items(), key=lambda x: x[1], reverse=True)[:top_k]
        out[st] = [w for w,_ in ranked]
    return out

def strategist_playbook(breakdown, market_hist, tsa_df, news_df):
    """Return dict with marketing posture, insight watchlist, topical signals, and per-state topics."""
    marketing, insight, topics = [], [], []

    # 1) Headline-driven tactical prompts by vertical
    if news_df is not None and not news_df.empty:
        titles = " ".join(news_df["title"].astype(str).tolist())
        for vert, pats in VERTICALS.items():
            if _match_any(titles, pats):
                if vert == "healthcare":
                    marketing.append("Activate **Healthcare** & **Pharma** audiences; test prevention & care messaging.")
                    insight.append("Monitor disease-topic velocity; align geo tactics near hospitals & clinics.")
                if vert == "travel":
                    marketing.append("Increase **Travel** intent targeting; sync bids to airport/TSA cadence.")
                    insight.append("Use weather-driven triggers for flight-disruption creatives in affected states.")
                if vert == "retail":
                    marketing.append("Lean into **Retail** deal creatives; day-part around shopping windows.")
                    insight.append("Track footfall deltas for malls; pivot to value messaging where inflation spikes.")
                if vert == "finance":
                    marketing.append("For **Finance**, foreground stability/returns; avoid risk-heavy creative during volatility.")
                    insight.append("Use VIX regime to adjust frequency caps; tighten brand-safety lists on earnings days.")
                if vert == "tech":
                    marketing.append("For **Tech**, reinforce privacy & reliability; steer away from outage-adjacent content.")
                    insight.append("Set alerts on ‘breach/outage’ terms; auto-pause sensitive placements.")
                if vert == "auto":
                    marketing.append("For **Auto**, retarget EV/ICE intent by fuel and rate headlines; test financing CTAs.")
                    insight.append("Layer gas-price proxies and DMV/registration signals if available.")

        # Emerging topics list (nationwide)
        for _, r in news_df.head(12).iterrows():
            topics.append("- " + " · ".join([
                str(r.get("title","")).strip()[:120],
                str(r.get("source","")).strip()
            ]))

    # 2) Regime hints from market/mobility
    try:
        last_vix = float(breakdown.get("components", {}).get("vix", {}).get("value", float("nan")))
    except Exception:
        last_vix = float("nan")
    if not pd.isna(last_vix):
        if last_vix >= 22:
            marketing.append("Shift tone **reassuring/credible**; prioritize top-of-funnel where confidence is shaky.")
        elif last_vix <= 15:
            marketing.append("Lean **bolder/product-led** creative; broaden prospecting where confidence is stable.")

    # 3) Per-state topic extraction for the UI (simple keywords per state)
    topics_by_state = _top_topics_by_state(news_df)

    return {
        "marketing": marketing[:6],
        "insight": insight[:6],
        "topics": topics,
        "topics_by_state": topics_by_state
    }
