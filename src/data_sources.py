import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load_json(name: str):
    p = ROOT / name
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def news_catalog():
    return load_json("news_rss_catalog.json")

def gov_catalog():
    return load_json("gov_regulatory_feeds.json")

def geo_cyber_catalog():
    return load_json("geo_cyber_event_feeds.json")

def incident_catalog():
    return load_json("incident_sources.json")

def social_catalog():
    return load_json("social_sources.json")
