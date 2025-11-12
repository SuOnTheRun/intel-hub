# src/methodology.py
from __future__ import annotations
from typing import Dict

METHODS: Dict[str, Dict[str, str]] = {
    # Page 1 — Command Center

    "tension_index": {
        "title": "National Tension Index",
        "formula": (
            "Composite of six components mapped to 0–100 via rolling percentile ranks, then "
            "combined by weighted average. Components: "
            "① News Tone (lower tone ⇒ higher risk), ② News Volume (higher ⇒ higher risk), "
            "③ CISA Advisories (higher ⇒ higher risk), ④ FEMA Declarations (higher ⇒ higher risk), "
            "⑤ VIX (higher ⇒ higher risk), ⑥ TSA Δ vs 2019 (lower ⇒ higher risk). "
            "Percentile rank is computed within each component’s own recent history window."
        ),
        "window": (
            "GDELT Tone & Volume: last 14 days; CISA: ~90 days (RSS-depth-limited); "
            "FEMA: ~90 days; VIX: up to last 365 days; TSA Δ: last ~180 days."
        ),
        "assumptions": (
            "No hard-coded priors. If a component lacks sufficient history (<8 points) or is empty, "
            "its contribution is set to neutral (50). Weights: Tone .30, Volume .10, CISA .15, FEMA .10, "
            "VIX .25, TSA .10. All sources are free & public."
        ),
        "sources": (
            "GDELT GKG v2; CISA Advisories RSS; FEMA OpenFEMA API; yfinance (^VIX); "
            "TSA Passenger Volumes CSV."
        )
    },

    "vix_level": {
        "title": "VIX (Market Stress)",
        "formula": "Latest ^VIX close/last price (CBOE Volatility Index proxy via yfinance).",
        "window": "Displayed value is latest; historical window up to 365 days for percentiles/momentum.",
        "assumptions": "If real-time price unavailable, falls back to last historical close.",
        "sources": "yfinance (^VIX)."
    },

    "tsa_delta": {
        "title": "Mobility Δ vs 2019",
        "formula": (
            "7-day moving average of current year passenger throughput vs 2019 7-day average: "
            "Δ% = ((Current7DMA − 2019_7DMA)/2019_7DMA)×100."
        ),
        "window": "Computed over the entire TSA series; UI shows latest value and 7-day drift.",
        "assumptions": "Official TSA CSV; missing recent days are handled by forward computation once posted.",
        "sources": "TSA Checkpoint Travel Numbers CSV."
    },

    "cisa_3d": {
        "title": "CISA Advisories (3 days)",
        "formula": "Count of advisories with published date in the last 3×24h (UTC).",
        "window": "RSS depth typically covers ~90 days; count recomputed on each fetch.",
        "assumptions": "No severity weighting; simple event count.",
        "sources": "CISA Advisories RSS."
    },

    "fema_14d": {
        "title": "FEMA Declarations (14 days)",
        "formula": "Count of disaster declarations with declarationDate in the last 14 days (UTC).",
        "window": "OpenFEMA paging to cover ~90 days; sum of last 14 daily counts.",
        "assumptions": "All incident types treated equally; count-based proxy for physical risk.",
        "sources": "FEMA OpenFEMA API."
    },

    "gdelt_tone": {
        "title": "News Tone (GDELT)",
        "formula": "Mean of GDELT GKG v2 'Tone' across US-related records in the selected window.",
        "window": "Shown as a 3-hour resampled mean over last ~48 hours; also used in 14-day component series.",
        "assumptions": "US filtering is textual (state names/US markers) on GKG locations string.",
        "sources": "GDELT GKG v2 daily CSV."
    },

    "market_momentum": {
        "title": "20-day Momentum (Indices)",
        "formula": "((Last / 20-day moving average) − 1) × 100, per index.",
        "window": "Computed on last ≤3 months of daily closes per index.",
        "assumptions": "If <21 points available, momentum shown as 0.00%.",
        "sources": "yfinance (^GSPC, ^NDX)."
    }
}

def method_note(key: str) -> str:
    m = METHODS.get(key, {})
    if not m:
        return ""
    return (
        f"**How this is calculated**  \n"
        f"- **Formula:** {m.get('formula','')}  \n"
        f"- **Window:** {m.get('window','')}  \n"
        f"- **Assumptions:** {m.get('assumptions','')}  \n"
        f"- **Sources:** {m.get('sources','')}"
    )
