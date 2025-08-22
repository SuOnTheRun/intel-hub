import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from rapidfuzz import fuzz
from .presets import REGION_PRESETS, region_keywords
import re
import pandas as pd
import numpy as np

EMOTION_KEYS = ["anger","anticipation","disgust","fear","joy","sadness","surprise","trust"]

# Minimal but real lexicon (expand later as needed)
_EMO_LEXICON = {
    "anger": {"anger","furious","rage","outrage","irate","hostile","resent","fume","wrath","hate","attack","retaliation","provocation"},
    "anticipation": {"anticipate","prepare","await","expect","upcoming","prospect","forecast","signal","likely","poised","build-up","mobilize"},
    "disgust": {"disgust","vile","abhorrent","revolting","corrupt","scandal","shameful","disgrace","repulsive","heinous"},
    "fear": {"fear","threat","terror","panic","worry","unsafe","attack","strike","escalation","airstrike","missile","dread","risk"},
    "joy": {"joy","relief","win","progress","growth","peace","stability","prosper","celebrate","boost","record"},
    "sadness": {"sad","grief","mourning","loss","deaths","casualties","downgrade","recession","decline","sorrow"},
    "surprise": {"surprise","shock","unexpected","sudden","unprecedented","abrupt","caught off guard","stunning"},
    "trust": {"trust","assure","pledge","agreement","deal","alliance","cooperate","support","aid","commit","credible"}
}

# Build inverse map: word -> set(emotions)
_WORD2EMO = {}
for emo, words in _EMO_LEXICON.items():
    for w in words:
        _WORD2EMO.setdefault(w.lower(), set()).add(emo)

_token_re = re.compile(r"[A-Za-z][A-Za-z\-']+")

def _fallback_emotions(text: str):
    """Return normalized scores per emotion using the built-in lexicon."""
    counts = {k: 0 for k in EMOTION_KEYS}
    if not isinstance(text, str) or not text.strip():
        return counts, ""
    for tok in _token_re.findall(text.lower()):
        emos = _WORD2EMO.get(tok)
        if emos:
            for e in emos:
                counts[e] += 1
    total = sum(counts.values())
    if total == 0:
        return counts, ""
    for e in counts:
        counts[e] = counts[e] / total
    dominant = max(counts, key=counts.get)
    return counts, dominant


# ---- NRC EmoLex optional import (safe) ----
_EMO_OK = False
try:
    from nrclex import NRCLex  # pip package: nrclex
    _EMO_OK = True
except Exception:
    class NRCLex:  # no-op fallback
        def __init__(self, text):
            self.raw_emotion_scores = {}

# ---- NRC emotion lexicon (optional) ----
# Robust, lazy import so the app never crashes if the package is missing.
_EMO_OK = False
try:
    import importlib
    NRCLex = importlib.import_module("nrclex").NRCLex  # pip package: nrclex
    _EMO_OK = True
except Exception:
    class NRCLex:  # no-op fallback
        def __init__(self, text):
            self.raw_emotion_scores = {}

_an = SentimentIntensityAnalyzer()

TOPIC_MAP = {
    "Security":  ["attack","strike","missile","drone","shelling","ceasefire","sanction","mobilization","military","naval","army","casualty","evacuate"],
    "Mobility":  ["flight","airport","airspace","rail","border","vessel","ship","tanker","port","blockade","notam"],
    "Markets":   ["markets","stocks","equity","bond","tariff","inflation","currency","oil","gas","commodity"],
    "Elections": ["election","vote","ballot","poll","campaign","parliament","rally"],
    "Technology":["ai","semiconductor","chip","cyber","data","cloud","satellite"],
    "Retail":    ["retail","consumer","footfall","ecommerce","store"],
    "Energy":    ["pipeline","refinery","power","grid","nuclear","renewable","solar","coal"],
}
TOPIC_LIST = list(TOPIC_MAP.keys())

SOURCE_WEIGHTS = {
    "reuters": 1.25, "bbc": 1.2, "associated press": 1.2, "ap": 1.2,
    "al jazeera": 1.1, "financial times": 1.15, "bloomberg": 1.15, "nytimes": 1.15
}
TOPIC_WEIGHTS = {"Security":1.6,"Mobility":1.3,"Elections":1.2,"Markets":1.15,"Energy":1.2,"Technology":1.1,"Retail":1.05}

def _ensure_utc(ts): return pd.to_datetime(ts, errors="coerce", utc=True)

def _classify_topic(text: str) -> str:
    t = (text or "").lower()
    for topic, keys in TOPIC_MAP.items():
        if any(k in t for k in keys):
            return topic
    return "General"

def _classify_region(text: str) -> str:
    t = (text or "").lower()
    for region, preset in REGION_PRESETS.items():
        keys = preset.get("keywords", [])
        if any(k in t for k in keys):
            return region
    return "Global"

def _vader_sent(text: str) -> float:
    if not isinstance(text, str): return 0.0
    return _an.polarity_scores(text)["compound"]

def enrich_news_with_topics_regions(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["source","published_ts","title","link","origin","region","topic","sentiment"])
    d = df.copy()
    d["published_ts"] = _ensure_utc(d["published_ts"] if "published_ts" in d.columns else d.get("published"))
    d["region"]    = d["title"].fillna("").apply(_classify_region)
    d["topic"]     = d["title"].fillna("").apply(_classify_topic)
    d["sentiment"] = d["title"].fillna("").apply(_vader_sent)
    return d

def _risk_row(row) -> float:
    recency_h = 12.0
    try:
        now_utc = pd.Timestamp.now(tz="UTC")
        if pd.notna(row.get("published_ts")):
            recency_h = max(0.25, (now_utc - row["published_ts"]).total_seconds()/3600.0)
    except Exception:
        pass
    tw = TOPIC_WEIGHTS.get(row.get("topic",""), 1.0)
    sw = 1.0
    s = (row.get("source") or "").lower()
    for k,v in SOURCE_WEIGHTS.items():
        if k in s: sw = v; break
    sent = row.get("sentiment", 0.0)
    sf = 1.1 + max(0.0, -sent)  # penalize negative less (actionable > purely negative)
    # boost for strong security words
    title = (row.get("title") or "").lower()
    if any(w in title for w in ["attack","strike","drone","missile","evacuate","casualty","explosion","airspace closed","notam"]):
        tw *= 1.15
    score = 100 * tw * sw * sf / (1 + 0.15*recency_h)
    return round(score, 1)

def add_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    d = df.copy()
    d["published_ts"] = _ensure_utc(d["published_ts"])
    d["risk"] = d.apply(_risk_row, axis=1)
    return d

def filter_by_controls(df: pd.DataFrame, region: str, topics: list, hours: int) -> pd.DataFrame:
    if df is None or df.empty: return df
    d = df.copy()
    d["published_ts"] = _ensure_utc(d["published_ts"])
    if region and region != "Global":
        d = d[d["region"] == region]
        if len(d) < 15:
            keys = region_keywords(region)
            if keys:
                d = pd.concat([d, df[df["title"].str.lower().str.contains("|".join(keys), na=False)]], ignore_index=True).drop_duplicates(subset=["link","title"])
    if topics:
        d = d[d["topic"].isin(topics)]
    if hours:
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=hours)
        d = d[d["published_ts"] >= cutoff]
        if len(d) < 20:
            # auto-widen the time window to avoid empty page
            cutoff2 = pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=96)
            d = pd.concat([d, df[df["published_ts"] >= cutoff2]], ignore_index=True).drop_duplicates(subset=["link","title"])
    return d

# ---- Clustering similar headlines (rapidfuzz) ----

def cluster_headlines(df: pd.DataFrame, sim: int = 70) -> pd.DataFrame:
    """Group near-duplicate titles; keep the highest-risk exemplar per cluster."""
    if df is None or df.empty: return df
    d = df.sort_values("risk", ascending=False).copy()
    used = set()
    clusters = []
    titles = d["title"].fillna("").tolist()
    for i, t in enumerate(titles):
        if i in used: continue
        group_idx = [i]
        for j in range(i+1, len(titles)):
            if j in used: continue
            if fuzz.token_set_ratio(t, titles[j]) >= sim:
                group_idx.append(j); used.add(j)
        used.add(i)
        exemplar = d.iloc[group_idx].sort_values("risk", ascending=False).iloc[0]
        exemplar["cluster_size"] = len(group_idx)
        clusters.append(exemplar)
    return pd.DataFrame(clusters)

def aggregate_kpis(news_df: pd.DataFrame, gdelt_df: pd.DataFrame, air_df: pd.DataFrame) -> dict:
    total_reports = (0 if news_df is None else len(news_df)) + (0 if gdelt_df is None else len(gdelt_df))
    high_risk_regions = (news_df[news_df["topic"].eq("Security")].groupby("region").size().shape[0]
                         if news_df is not None and not news_df.empty else 0)
    aircraft_tracked = 0 if air_df is None else len(air_df)
    movement_detections = (air_df["on_ground"] == False).sum() if air_df is not None and not air_df.empty else 0
    avg_risk = round(max(0, min(10, 5 + (high_risk_regions/4))), 1)
    return dict(total_reports=total_reports, movement=movement_detections,
                high_risk_regions=high_risk_regions, aircraft=aircraft_tracked, avg_risk=avg_risk)

def build_social_listening_panels(news_df: pd.DataFrame, reddit_df: pd.DataFrame):
    blocks = []
    if news_df is not None and not news_df.empty:
        top_regions = news_df.groupby("region").size().sort_values(ascending=False).head(6).index.tolist()
        for r in top_regions:
            subset = news_df[news_df["region"] == r][["published_ts","topic","title","risk","sentiment","source","origin","link"]].head(50)
            blocks.append({"title": f"Region — {r}", "table": subset})
    if reddit_df is not None and not reddit_df.empty:
        rr = reddit_df.sort_values("created_utc", ascending=False).head(100)
        blocks.append({"title": "Reddit — Latest Posts", "table": rr[["created_utc","subreddit","title","score","url","query"]]})
    return blocks

# ========= EMOTION, VELOCITY, EARLY-WARNING UTILITIES =========
import pandas as pd
import numpy as np

# Safe import: do not crash if pip didn't install nrclex yet
try:
    from nrclex import NRCLex  # pip package name: nrclex
    _EMO_OK = True
except Exception:
    _EMO_OK = False
    class NRCLex:  # no-op fallback so the app keeps running
        def __init__(self, text):
            self.raw_emotion_scores = {}

EMOTION_KEYS = ["anger","anticipation","disgust","fear","joy","sadness","surprise","trust"]

def _safe_text(x):
    if isinstance(x, str) and x.strip():
        return x.strip()
    return ""
def add_emotions(df, text_col="title"):
    """
    Adds emotion proportions per row.
    Prefers NRCLex when available; falls back to built-in lexicon otherwise.
    Creates columns: emo_anger...emo_trust, emo_dominant
    """
    if df is None or df.empty:
        return df

    # Ensure columns exist
    for k in EMOTION_KEYS:
        col = f"emo_{k}"
        if col not in df.columns:
            df[col] = 0.0
    if "emo_dominant" not in df.columns:
        df["emo_dominant"] = ""

    if _EMO_OK:
        # NRCLex path
        dom = []
        for idx, t in enumerate(df[text_col].astype(str).fillna("")):
            emo = NRCLex(t)
            raw = getattr(emo, "raw_emotion_scores", {}) or {}
            total = sum(raw.values()) or 1
            for k in EMOTION_KEYS:
                df.at[df.index[idx], f"emo_{k}"] = raw.get(k, 0) / total
            dom.append(max(raw, key=raw.get) if raw else "")
        df["emo_dominant"] = dom
        return df
    else:
        # Fallback lexicon path (no extra pip deps)
        dom = []
        for idx, t in enumerate(df[text_col].astype(str).fillna("")):
            scores, top = _fallback_emotions(t)
            for k in EMOTION_KEYS:
                df.at[df.index[idx], f"emo_{k}"] = scores.get(k, 0.0)
            dom.append(top)
        df["emo_dominant"] = dom
        return df



    # initialize columns if missing
    for k in EMOTION_KEYS:
        col = f"emo_{k}"
        if col not in df.columns:
            df[col] = 0.0

    dom = []
    for idx, t in enumerate(df[text_col].astype(str).fillna("")):
        text = _safe_text(t)
        if not text:
            dom.append("")
            continue
        emo = NRCLex(text)
        raw = emo.raw_emotion_scores or {}
        total = sum(raw.values()) or 1
        for k in EMOTION_KEYS:
            df.at[df.index[idx], f"emo_{k}"] = raw.get(k, 0) / total
        dom.append(max(raw, key=raw.get) if raw else "")
    df["emo_dominant"] = dom
    return df

def compute_event_velocity(df, time_col="published"):
    """
    Returns {'events_per_hour': float, 'by_topic': {topic: float}}.
    Robust to missing/varied timestamp columns and bad values.
    """
    if df is None or df.empty:
        return {"events_per_hour": 0.0, "by_topic": {}}

    # 1) pick the best available time column
    candidates = [time_col, "published", "published_at", "date", "datetime", "timestamp", "time", "ts"]
    col = next((c for c in candidates if c in df.columns), None)
    if col is None:
        return {"events_per_hour": 0.0, "by_topic": {}}

    s = df.copy()

    # 2) force to datetime, coerce bad rows to NaT, keep only valid
    s[col] = pd.to_datetime(s[col], errors="coerce", utc=True)
    s = s.dropna(subset=[col])
    if s.empty:
        return {"events_per_hour": 0.0, "by_topic": {}}

    # 3) hourly bucket
    s["hour_bucket"] = s[col].dt.floor("H")

    # 4) global velocity over last 24 buckets (or all if fewer)
    by_hour = s.groupby("hour_bucket").size().sort_index()
    window = by_hour.tail(24)
    events_per_hour = window.mean() if len(window) else float(by_hour.mean())

    # 5) per-topic velocity (if topic exists)
    by_topic = {}
    if "topic" in s.columns:
        topic_hour = s.groupby(["hour_bucket", "topic"]).size().unstack(fill_value=0).sort_index()
        topic_window = topic_hour.tail(24) if len(topic_hour) else topic_hour
        by_topic = topic_window.mean().to_dict() if not topic_window.empty else {}

    return {"events_per_hour": float(events_per_hour), "by_topic": {k: float(v) for k, v in by_topic.items()}}


def compute_mobility_anomalies(air_df):
    if air_df is None or air_df.empty:
        return 0
    uniq = air_df["icao24"].nunique() if "icao24" in air_df.columns else 0
    return int(uniq)

def compute_early_warning(df, gdelt_df=None, air_df=None):
    if df is None:
        df = pd.DataFrame()
    pool = df
    if gdelt_df is not None and not gdelt_df.empty:
        pool = pd.concat([pool, gdelt_df], ignore_index=True)
    if pool is None or pool.empty:
        return 0.0
    risk = pool["risk_score"].mean() if "risk_score" in pool.columns else 0.0
    risk_norm = np.clip(risk / 10.0, 0, 1)
    for k in EMOTION_KEYS:
        if f"emo_{k}" not in pool.columns:
            pool[f"emo_{k}"] = 0.0
    emo_neg = (pool["emo_fear"] + pool["emo_anger"] + pool["emo_sadness"]).mean()
    emo_pos = (pool["emo_joy"] + pool["emo_trust"]).mean()
    emo_tilt = np.clip((emo_neg - emo_pos + 1) / 2, 0, 1)
    vel = compute_event_velocity(pool).get("events_per_hour", 0.0)
    vel_norm = np.tanh(vel / 6.0)
    mob = compute_mobility_anomalies(air_df) if air_df is not None else 0
    mob_norm = np.tanh(mob / 40.0)
    index_0_10 = 10.0 * (0.35*risk_norm + 0.25*emo_tilt + 0.25*vel_norm + 0.15*mob_norm)
    return round(float(index_0_10), 1)

def extend_kpis_with_intel(kpis, news_df, gdelt_df, air_df):
    if kpis is None:
        kpis = {}
    # enrich with emotions (no-op if _EMO_OK is False)
    news_df = add_emotions(news_df) if (news_df is not None and not news_df.empty) else news_df
    if gdelt_df is not None and not getattr(gdelt_df, "empty", True):
        gdelt_df = add_emotions(gdelt_df)
    kpis["early_warning"] = compute_early_warning(news_df, gdelt_df, air_df)
    from pandas import concat
    pool = concat([news_df, gdelt_df], ignore_index=True) if (gdelt_df is not None and not gdelt_df.empty) else news_df
    vel = compute_event_velocity(pool).get("events_per_hour", 0.0) if (pool is not None and not pool.empty) else 0.0
    kpis["event_velocity"] = round(float(vel), 2)
    kpis["mobility_anomalies"] = compute_mobility_anomalies(air_df)
    if pool is not None and not pool.empty:
        for k in EMOTION_KEYS:
            col = f"emo_{k}"
            if col in pool.columns:
                kpis[col] = round(float(pool[col].mean()), 3)
        if "emo_dominant" in pool.columns and not pool["emo_dominant"].empty:
            kpis["emo_dominant_top"] = pool["emo_dominant"].value_counts().idxmax()
    return kpis
