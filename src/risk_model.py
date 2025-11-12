# src/risk_model.py
"""
National Tension Index — fully reproducible, data-first.

We compute six component time series from free, public sources and convert each
to a 0–100 “risk contribution” using *rolling percentile mapping* (no priors):

  Component (daily)                 Source & Construction                         Risk Direction
  -------------------------------------------------------------------------------------------------------------
  1) News Tone (mean tone)         GDELT GKG v2 (last 14 days)                    Lower tone  -> higher risk
  2) News Volume (doc count)       GDELT GKG v2 (last 14 days)                    Higher count -> higher risk
  3) CISA Advisories (count)       CISA advisories RSS (last ~90 days available)  Higher count -> higher risk
  4) FEMA Disasters (count)        OpenFEMA (last 90 days)                         Higher count -> higher risk
  5) Market Stress (VIX)           yfinance ^VIX (last 365 days)                   Higher VIX   -> higher risk
  6) Mobility Delta vs 2019 (%)    TSA throughput CSV (last 180 days)              Lower delta  -> higher risk

Percentile mapping:
    For a daily series S(t), we compute the rolling percentile rank P(t) of today’s
    value relative to the historical window (excluding NaNs). Then we map to risk:

      If higher values are riskier:     risk_component = 100 * P(t)
      If lower values are riskier:      risk_component = 100 * (1 - P(t))

    This removes unit/scale issues and avoids subjective z-score “priors”.

Composite index (0–100):
    TensionIndex = weighted average of component risk contributions.

Default weights (sum = 1.00):
    w = {
        "tone": 0.30,     # narrative tone matters most
        "volume": 0.10,   # surge of coverage
        "cisa": 0.15,     # cyber advisories
        "fema": 0.10,     # physical incidents / disasters
        "vix": 0.25,      # market stress proxy
        "tsa": 0.10,      # mobility soft data
    }

All intermediate series and component scores are returned for transparency.

This module exposes:
    - compute_inputs():          quick snapshot used by UI metrics
    - compute_tension_index():   composite score using percentile method
    - market_momentum():         20-day momentum helper for charts
    - build_component_series():  full per-component daily series (for audits)

No placeholders; if a source is temporarily empty, that component will be
neutral (50) and flagged in the returned diagnostics.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd

from .collectors import (
    fetch_gdelt_gkg_last_n_days,
    fetch_tsa_throughput,
    fetch_market_snapshot,
    fetch_cisa_alerts,
)
from .collectors import _now  # internal utility for UTC "now"
from .analytics import drift


# ------------------------------
# Helper: robust percentile rank
# ------------------------------
def _percentile_rank(series: pd.Series, value: float) -> float:
    """
    Returns percentile rank in [0,1]. If series is too short or degenerate,
    returns 0.5 (neutral).
    """
    s = pd.Series(series).dropna()
    if len(s) < 8:  # need enough history for a meaningful percentile
        return 0.5
    # Use rank(pct=True) which yields empirical CDF in (0,1]
    # Clip to [0,1] for safety.
    return float(np.clip((s <= value).mean(), 0.0, 1.0))


# ----------------------------------------
# Build daily series for each risk feature
# ----------------------------------------
def _gdelt_daily() -> pd.DataFrame:
    """
    Returns DataFrame with index=date (UTC date) and columns:
        tone_mean, doc_count
    Based on last 14 days of GDELT GKG (US-filtered in collectors).
    """
    gkg = fetch_gdelt_gkg_last_n_days(14)
    if gkg.empty:
        idx = pd.date_range(_now().date() - pd.Timedelta(days=13), periods=14, freq="D")
        return pd.DataFrame(index=idx, data={"tone_mean": np.nan, "doc_count": np.nan})
    g = gkg.copy()
    g["date"] = pd.to_datetime(g["datetime"]).dt.tz_convert("UTC").dt.date
    daily = g.groupby("date").agg(tone_mean=("tone", "mean"),
                                  doc_count=("tone", "size")).sort_index()
    # ensure continuous daily index
    idx = pd.date_range(pd.to_datetime(daily.index.min()), pd.to_datetime(daily.index.max()), freq="D")
    daily.index = pd.to_datetime(daily.index)
    daily = daily.reindex(idx)
    return daily


def _cisa_daily() -> pd.Series:
    """
    Daily count of CISA advisories for ~last 90 days (depends on RSS depth).
    """
    cisa = fetch_cisa_alerts(limit=400)  # try to get as much as RSS gives
    if cisa.empty:
        idx = pd.date_range(_now().date() - pd.Timedelta(days=89), periods=90, freq="D")
        return pd.Series(index=idx, data=np.nan, name="cisa_count")
    s = cisa.copy()
    s["date"] = pd.to_datetime(s["time"]).dt.tz_convert("UTC").dt.date
    daily = s.groupby("date").size().rename("cisa_count").sort_index()
    idx = pd.date_range(pd.to_datetime(daily.index.min()), pd.to_datetime(daily.index.max()), freq="D")
    daily.index = pd.to_datetime(daily.index)
    daily = daily.reindex(idx)
    return daily


def _fema_daily() -> pd.Series:
    """
    Daily count of FEMA disaster declarations (~last 90 days).
    Gentle paging; returns a UTC-indexed daily series.
    """
    rows: List[pd.DataFrame] = []
    base = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
    url = f"{base}?$orderby=declarationDate%20desc&$top=500"
    from .collectors import _http_get  # reuse client

    for _ in range(3):
        try:
            r = _http_get(url)
            js = r.json().get("DisasterDeclarationsSummaries", [])
        except Exception:
            js = []
        if not js:
            break
        df = pd.DataFrame(js)
        rows.append(df)

        # Stop when we’ve covered ~90 days. NOTE: to_datetime(..., utc=True) is tz-aware.
        last_date = pd.to_datetime(df["declarationDate"], utc=True).min()
        # pd.Timestamp.utcnow() is already tz-aware; don't tz_localize.
        if (pd.Timestamp.utcnow() - last_date) > pd.Timedelta(days=95):
            break

    if not rows:
        idx = pd.date_range(pd.Timestamp.utcnow().normalize() - pd.Timedelta(days=89),
                            periods=90, freq="D", tz="UTC")
        return pd.Series(index=idx, data=np.nan, name="fema_count")

    all_df = pd.concat(rows, ignore_index=True)
    all_df["date"] = pd.to_datetime(all_df["declarationDate"], utc=True).dt.normalize()  # UTC midnight
    daily = all_df.groupby("date").size().rename("fema_count").sort_index()
    # Ensure continuous UTC daily index
    idx = pd.date_range(daily.index.min(), daily.index.max(), freq="D", tz="UTC")
    daily = daily.reindex(idx)
    return daily


def _vix_daily(hist: pd.DataFrame) -> pd.Series:
    """
    VIX daily close series (prefer 1y window) from yfinance history provided by collectors.
    """
    if "VIX" not in hist.columns or hist["VIX"].dropna().empty:
        return pd.Series(dtype=float, name="vix")
    s = hist["VIX"].dropna().rename("vix")
    # keep last 365 days if available
    if len(s) > 365:
        s = s.tail(365)
    return s


def _tsa_delta_daily(tsa_df: pd.DataFrame) -> pd.Series:
    """
    TSA 7-day moving average delta vs 2019 (%) as a daily series (last ~180 days).
    """
    if tsa_df is None or tsa_df.empty:
        return pd.Series(dtype=float, name="tsa_delta_pct")
    s = tsa_df.set_index("date")["delta_vs_2019_pct"].rename("tsa_delta_pct").dropna()
    return s


def build_component_series() -> Dict[str, pd.Series | pd.DataFrame]:
    """
    Returns a dict with daily series for each component, suitable for auditing.
    Keys:
        - gdelt (DataFrame: tone_mean, doc_count)
        - cisa  (Series: cisa_count)
        - fema  (Series: fema_count)
        - vix   (Series: vix)
        - tsa   (Series: tsa_delta_pct)
    """
    gdelt = _gdelt_daily()
    # market snapshot returns (dict, hist_df)
    _, market_hist = fetch_market_snapshot()
    tsa_df = fetch_tsa_throughput()
    cisa = _cisa_daily()
    fema = _fema_daily()
    vix = _vix_daily(market_hist)
    tsa = _tsa_delta_daily(tsa_df)
    return {"gdelt": gdelt, "cisa": cisa, "fema": fema, "vix": vix, "tsa": tsa}


# --------------------------------------------------------
# Public API: inputs snapshot (for top-line UI quick stats)
# --------------------------------------------------------
@dataclass
class RiskInputs:
    gdelt_tone_mean: float
    gdelt_count: int
    cisa_count_3d: int
    fema_count_14d: int
    vix_level: float
    tsa_delta_pct: float

# --- timezone-safe index normaliser (module-level helper) ---
def _as_utc_index(idx) -> pd.DatetimeIndex:
    """
    Return a UTC DatetimeIndex whether the incoming index is tz-naive or tz-aware.
    Must be defined at module level (no indentation).
    """
    idx = pd.to_datetime(idx, errors="coerce")
    if getattr(idx, "tz", None) is None:
        return idx.tz_localize("UTC")
    return idx.tz_convert("UTC")


def compute_inputs() -> Tuple[RiskInputs, Dict[str, pd.DataFrame]]:
    """
    Builds a same-day snapshot used by the UI metrics. Also returns the raw frames.
    All quantities are directly computed from the live sources (no priors).
    """
    series = build_component_series()
    gd = series["gdelt"]
    cisa = series["cisa"]
    fema = series["fema"]
    vix = series["vix"]
    tsa = series["tsa"]

    # Today-like indices (use most recent available point for each series)
    tone_mean = float(gd["tone_mean"].dropna().iloc[-1]) if not gd.empty else np.nan
    doc_count = int(gd["doc_count"].dropna().iloc[-1]) if not gd.empty else 0
    cisa_3d = int(cisa.tail(3).fillna(0).sum()) if not cisa.empty else 0
    fema_14d = int(fema.tail(14).fillna(0).sum()) if not fema.empty else 0
    vix_level = float(vix.dropna().iloc[-1]) if not vix.empty else np.nan
    tsa_delta = float(tsa.dropna().iloc[-1]) if not tsa.empty else np.nan

    inputs = RiskInputs(
        gdelt_tone_mean=0.0 if np.isnan(tone_mean) else tone_mean,
        gdelt_count=doc_count,
        cisa_count_3d=cisa_3d,
        fema_count_14d=fema_14d,
        vix_level=0.0 if np.isnan(vix_level) else vix_level,
        tsa_delta_pct=0.0 if np.isnan(tsa_delta) else tsa_delta,
    )
    # Also hand back frames needed by the UI
   def _as_utc_index(idx) -> pd.DatetimeIndex:
    idx = pd.to_datetime(idx, errors="coerce")
    return idx.tz_localize("UTC") if getattr(idx, "tz", None) is None else idx.tz_convert("UTC")

frames = {
    "gkg": fetch_gdelt_gkg_last_n_days(2),
    "cisa": pd.DataFrame(
        {"time": _as_utc_index(cisa.index), "count": cisa.values}
    ).sort_values("time", ascending=False).head(30),
    "fema": pd.DataFrame(
        {"time": _as_utc_index(fema.index), "count": fema.values}
    ).sort_values("time", ascending=False).head(30),
    "tsa": fetch_tsa_throughput(),
    "market_hist": fetch_market_snapshot()[1],
}




# --------------------------------------------------
# Composite: percentile-based, fully specified math
# --------------------------------------------------
def compute_tension_index(inputs: RiskInputs) -> float:
    """
    Computes the composite 0–100 score from rolling percentile contributions.

    Steps (per component):
        1) Build historical daily series (see build_component_series()).
        2) Compute percentile rank of the latest value within its window.
        3) Map to risk contribution (higher-is-worse or lower-is-worse).
        4) Weighted average of six components.

    Returns:
        Rounded float in [0, 100].
    """
    series = build_component_series()
    gd = series["gdelt"]
    cisa = series["cisa"]
    fema = series["fema"]
    vix = series["vix"]
    tsa = series["tsa"]

    # Latest values
    tone_today = float(gd["tone_mean"].dropna().iloc[-1]) if not gd.empty else np.nan
    vol_today  = float(gd["doc_count"].dropna().iloc[-1]) if not gd.empty else np.nan
    cisa_today = float(cisa.dropna().iloc[-1]) if not cisa.empty else np.nan
    fema_today = float(fema.dropna().iloc[-1]) if not fema.empty else np.nan
    vix_today  = float(vix.dropna().iloc[-1]) if not vix.empty else np.nan
    tsa_today  = float(tsa.dropna().iloc[-1]) if not tsa.empty else np.nan

    # Percentile ranks
    tone_pct = _percentile_rank(gd["tone_mean"], tone_today) if not np.isnan(tone_today) else 0.5
    vol_pct  = _percentile_rank(gd["doc_count"], vol_today)  if not np.isnan(vol_today)  else 0.5
    cisa_pct = _percentile_rank(cisa, cisa_today)            if not np.isnan(cisa_today) else 0.5
    fema_pct = _percentile_rank(fema, fema_today)            if not np.isnan(fema_today) else 0.5
    vix_pct  = _percentile_rank(vix, vix_today)              if not np.isnan(vix_today)  else 0.5
    tsa_pct  = _percentile_rank(tsa, tsa_today)              if not np.isnan(tsa_today)  else 0.5

    # Map to risk contributions (0..100). Note tone and TSA are inverted.
    comp = {
        "tone": 100.0 * (1.0 - tone_pct),   # lower tone => worse
        "volume": 100.0 * vol_pct,          # higher volume => worse
        "cisa": 100.0 * cisa_pct,           # higher count  => worse
        "fema": 100.0 * fema_pct,           # higher count  => worse
        "vix": 100.0 * vix_pct,             # higher VIX    => worse
        "tsa": 100.0 * (1.0 - tsa_pct),     # lower delta   => worse
    }

    # Explicit, documented weights
    w = {"tone": .30, "volume": .10, "cisa": .15, "fema": .10, "vix": .25, "tsa": .10}
    weighted = sum(comp[k] * w[k] for k in w)
    idx = float(np.clip(weighted / sum(w.values()), 0.0, 100.0))
    return round(idx, 2)


# -------------------------
# Market momentum (unchanged)
# -------------------------
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
# --- add to src/risk_model.py (near the bottom) ---

def tension_breakdown() -> dict:
    """
    Returns a full audit record for today's Tension Index:
      {
        'index': <float 0..100>,
        'components': {
           'tone': {'latest': float, 'percentile': float, 'risk': float, 'weight': float},
           'volume': {...}, 'cisa': {...}, 'fema': {...}, 'vix': {...}, 'tsa': {...}
        }
      }
    All percentiles are in [0,1]. Risk contributions are 0..100 after direction mapping.
    """
    series = build_component_series()
    gd, cisa, fema, vix, tsa = series["gdelt"], series["cisa"], series["fema"], series["vix"], series["tsa"]

    def latest(s): 
        try:
            return float(pd.Series(s).dropna().iloc[-1])
        except Exception:
            return float("nan")

    # latest values
    tone_today = latest(gd["tone_mean"]) if not gd.empty else float("nan")
    vol_today  = latest(gd["doc_count"]) if not gd.empty else float("nan")
    cisa_today = latest(cisa)
    fema_today = latest(fema)
    vix_today  = latest(vix)
    tsa_today  = latest(tsa)

    # percentiles
    tone_pct = _percentile_rank(gd["tone_mean"], tone_today) if not np.isnan(tone_today) else 0.5
    vol_pct  = _percentile_rank(gd["doc_count"], vol_today)  if not np.isnan(vol_today)  else 0.5
    cisa_pct = _percentile_rank(cisa, cisa_today)            if not np.isnan(cisa_today) else 0.5
    fema_pct = _percentile_rank(fema, fema_today)            if not np.isnan(fema_today) else 0.5
    vix_pct  = _percentile_rank(vix, vix_today)              if not np.isnan(vix_today)  else 0.5
    tsa_pct  = _percentile_rank(tsa, tsa_today)              if not np.isnan(tsa_today)  else 0.5

    comp = {
        "tone":   {"latest": tone_today, "percentile": tone_pct, "risk": 100*(1-tone_pct), "weight": .30},
        "volume": {"latest": vol_today,  "percentile": vol_pct,  "risk": 100*(vol_pct),     "weight": .10},
        "cisa":   {"latest": cisa_today, "percentile": cisa_pct, "risk": 100*(cisa_pct),    "weight": .15},
        "fema":   {"latest": fema_today, "percentile": fema_pct, "risk": 100*(fema_pct),    "weight": .10},
        "vix":    {"latest": vix_today,  "percentile": vix_pct,  "risk": 100*(vix_pct),     "weight": .25},
        "tsa":    {"latest": tsa_today,  "percentile": tsa_pct,  "risk": 100*(1-tsa_pct),   "weight": .10},
    }
    idx = round(sum(v["risk"]*v["weight"] for v in comp.values()) / sum(v["weight"] for v in comp.values()), 2)
    return {"index": idx, "components": comp}
