# src/risk_model.py
import pandas as pd

def purchase_outlook_from_bri(bri_value: float) -> dict:
    """
    Interprets BRI (z-weighted composite) into a near-term purchase propensity outlook.
    """
    if pd.isna(bri_value):
        return {"outlook": "No Signal", "explanation": "Insufficient inputs"}
    if bri_value >= 1.0:
        return {"outlook": "Rising Demand", "explanation": "Search & sentiment momentum with supportive macro"}
    if bri_value >= 0.3:
        return {"outlook": "Stable to Positive", "explanation": "Neutral macro with improving intent/sentiment"}
    if bri_value <= -1.0:
        return {"outlook": "Softening", "explanation": "Fading intent and negative tone; monitor"}
    return {"outlook": "Neutral", "explanation": "Mixed signals; wait for confirmation"}
