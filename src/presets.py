# Region presets: bbox = "minLat,minLon,maxLat,maxLon"
REGION_PRESETS = {
    "Global":        {"bbox": None,                 "center": (20.0,   0.0),  "keywords": []},
    "Eastern Europe":{"bbox": "44,20,56,42",        "center": (49.0,  31.0),  "keywords": ["ukraine","russia","belarus","poland","kyiv","donetsk","kharkiv"]},
    "Israel–Gaza":   {"bbox": "29,33,34,36",        "center": (31.5,  34.8),  "keywords": ["israel","gaza","palestine","jerusalem","idf","hamas","hezbollah"]},
    "Red Sea":       {"bbox": "10,38,22,49",        "center": (15.0,  43.0),  "keywords": ["red sea","houthi","aden","yemen","suez"]},
    "Taiwan Strait": {"bbox": "21,117,27,124",      "center": (24.0, 121.0),  "keywords": ["taiwan","taipei","pla","strait","kinmen","matsu"]},
    "South China Sea":{"bbox":"1,105,23,121",       "center": (12.0, 113.0),  "keywords": ["spratly","paracel","philippines","palawan","reed bank","brp"]},
    "Indo-Pacific":  {"bbox": "5,60,35,140",        "center": (20.0, 100.0),  "keywords": ["india","indo-pacific","australia","japan","andaman","malacca"]},
    "South Asia":    {"bbox": "5,60,35,92",         "center": (20.0,  78.0),  "keywords": ["india","pakistan","bangladesh","sri lanka","nepal"]},
    "Europe":        {"bbox": "36,-10,60,30",       "center": (48.0,  10.0),  "keywords": ["europe","france","germany","uk","italy","spain"]},
    "Americas":      {"bbox": "-60,-130,60,-30",    "center": (15.0, -80.0),  "keywords": ["united states","canada","brazil","mexico","argentina"]},
    "Africa":        {"bbox": "-35,-20,38,52",      "center": ( 6.0,  20.0),  "keywords": ["nigeria","kenya","south africa","ethiopia","egypt","sahel"]},
}

def region_names():
    return list(REGION_PRESETS.keys())

def region_bbox(name: str):
    p = REGION_PRESETS.get(name, {})
    return p.get("bbox")

def region_center(name: str):
    p = REGION_PRESETS.get(name, {})
    return p.get("center", (20.0, 0.0))

def region_keywords(name: str):
    p = REGION_PRESETS.get(name, {})
    return p.get("keywords", [])
