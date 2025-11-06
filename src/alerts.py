import pandas as pd

def check_thresholds(kpis: pd.DataFrame, risk: pd.DataFrame):
    alerts = []
    for _, r in risk.iterrows():
        if r["tension_index"] >= 70:
            alerts.append(f"High tension in {r['category']}: {r['tension_index']}")
    return alerts
