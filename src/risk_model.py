# src/risk_model.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from .collectors import (
    fetch_gdelt_gkg_last_n_days, fetch_tsa_throughput,
    fetch_market_snapshot, fetch_cisa_alerts, fetch_fema_disasters
)
from .analytics import sentiment_score

@dataclass
class RiskInputs:
    gdelt_tone_mean: float
    gdelt_count: int
    cisa_count_3d: int
    fema_count_14d: int
    vix_level: float
    tsa_delta_pct: float

def _z(x: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return (x - mean) / std

def compute_inputs() -> Tuple[RiskInputs, Dict[str, pd.DataFrame]]:
    # GDELT (tone + volume)
    gkg = fetch_gdelt_gkg_last_n_days(2)
    tone = float(gkg["tone"].mean()) if not gkg.empty else 0.0
    count = int(len(gkg))

    # CISA last 3 days
    cisa = fetch_cisa_alerts(limit=100)
    cisa_3d = 0
    if not cisa.empty:
        cisa_3d = int((pd.Timestamp.utcnow().tz_localize("UTC") - cisa["time"]) <= pd.Timedelta(days=3)).sum()

    # FEMA last 14 days
    fema = fetch_fema_disasters(limit=100)
    fema_14d = 0
    if not fema.empty:
        fema_14d = int((pd.Timestamp.utcnow().tz_localize("UTC") - fema["time"]) <= pd.Timedelta(days=14)).sum()

    # Markets
    snap, hist = fetch_market_snapshot()
    vix = float(snap.get("VIX", np.nan))
    if np.isnan(vix):
        vix = float(hist["VIX"].iloc[-1]) if "VIX" in hist and not hist["VIX"].empty else 18.0

    # TSA delta vs 2019
    tsa = fetch_tsa_throughput()
    tsa_delta = float(tsa["delta_vs_2019_pct"].iloc[-1]) if not tsa.empty else 0.0

    inputs = RiskInputs(
        gdelt_tone_mean=tone,
        gdelt_count=count,
        cisa_count_3d=cisa_3d,
        fema_count_14d=fema_14d,
        vix_level=vix,
        tsa_delta_pct=tsa_delta,
    )
    return inputs, {"gkg": gkg, "cisa": cisa, "fema": fema, "tsa": tsa, "market_hist": hist}

def compute_tension_index(inputs: RiskInputs) -> float:
    """
    Composite 0–100. Higher = more tension.
    Components are normalized by robust ranges to keep stability on free-tier data.
    """
    # Robust z-scaling assumptions (fallback priors)
    tone_z     = -inputs.gdelt_tone_mean / 1.5           # tone more negative => more risk
    volume_z   = (inputs.gdelt_count - 20000) / 15000.0  # relative to typical daily US mentions
    cisa_z     = (inputs.cisa_count_3d - 6) / 4.0
    fema_z     = (inputs.fema_count_14d - 10) / 8.0
    vix_z      = (inputs.vix_level - 18) / 8.0
    tsa_z      = -(inputs.tsa_delta_pct) / 10.0          # below baseline increases risk

    # Weights
    w = dict(tone=.35, volume=.15, cisa=.15, fema=.10, vix=.20, tsa=.05)
    score = (
        w["tone"]*tone_z + w["volume"]*volume_z + w["cisa"]*cisa_z +
        w["fema"]*fema_z + w["vix"]*vix_z + w["tsa"]*tsa_z
    )
    # Map z-ish score to 0-100 via logistic-like squashing
    pct = float(100 / (1 + np.exp(-score)) )
    return round(pct, 2)

def market_momentum(hist: pd.DataFrame) -> Dict[str, float]:
    out = {}
    for col in hist.columns:
        s = hist[col].dropna()
        if len(s) < 21: 
            out[col] = 0.0
            continue
        mom = (s.iloc[-1] / s.rolling(20).mean().iloc[-1] - 1) * 100
        out[col] = float(round(mom, 2))
    return out
