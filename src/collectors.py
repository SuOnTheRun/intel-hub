# --- BROAD RSS COVERAGE (BBC / Al Jazeera / AP / DW / CNBC / FT / Reuters / Guardian / CNN) ---
RSS_FEEDS = [
    # BBC
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    # Al Jazeera
    "https://www.aljazeera.com/xml/rss/all.xml",
    # AP
    "https://apnews.com/hub/apf-topnews?utm_source=rss",
    "https://apnews.com/hub/apf-business?utm_source=rss",
    # Deutsche Welle
    "https://rss.dw.com/rdf/rss-en-ger",
    "https://rss.dw.com/rdf/rss-en-top",
    # CNBC
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",   # Top
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",   # Tech
    "https://www.cnbc.com/id/10000108/device/rss/rss.html",   # Business
    # Financial Times (public home)
    "https://www.ft.com/rss/home/uk",
    # Reuters
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/worldNews",
    # The Guardian
    "https://www.theguardian.com/world/rss",
    "https://www.theguardian.com/business/rss",
    # CNN Business
    "http://rss.cnn.com/rss/money_latest.rss",
]

def _geo_match(text: str, country: Optional[str], region: Optional[str]) -> bool:
    if not country and not region: 
        return True
    t = text.lower()
    if country and country.lower() in t: return True
    if region and region.lower() in t: return True
    return False

def _keyword(text: str, kws: List[str]) -> bool:
    # light OR – we only need 1 hit
    b = text.lower()
    return any(re.search(rf"\b{k}\b", b) for k in kws)

def _score(title: str, summary: str) -> Dict[str, float]:
    s = analyzer.polarity_scores(title)["compound"]
    emo = emotion_scores(f"{title}. {summary}")
    return {"senti": float(s), "emotions": emo}

def fetch_news_rss(category: str, country: Optional[str], region: Optional[str], limit: int=120) -> List[Dict[str,Any]]:
    """Pull widely; do a light keyword+geo filter; if that yields too few, return top items unfiltered (graceful fallback)."""
    kws = CATEGORIES[category]["keywords"]
    candidates, fallback = [], []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:60]:
                title = e.get("title","") or ""
                summary = e.get("summary","") or ""
                link = e.get("link"); pub = e.get("published","")
                src  = re.sub(r"^https?://(www\\.)?","", url).split('/')[0]
                item = {"title": title, "summary": summary, "link": link, "published": pub, "source": src}
                fallback.append(item)  # keep a copy for the fallback path
                blob = f"{title} {summary}"
                if _keyword(blob, kws) and _geo_match(blob, country, region):
                    candidates.append(item)
        except Exception:
            continue

    # Prefer filtered matches; if too few, pad with top recent items regardless of keywords so the UI is never empty.
    rows = candidates[:limit]
    if len(rows) < max(30, int(0.25*limit)):
        pad = [x for x in fallback if x not in rows]
        rows = (rows + pad)[:limit]

    # Score sentiment/emotions
    out=[]
    for r in rows:
        sc = _score(r["title"], r["summary"])
        out.append({**r, **sc})
    return out

def fetch_news_newsapi(category: str, country: Optional[str], region: Optional[str], limit:int=100) -> List[Dict[str,Any]]:
    if not NEWSAPI_KEY:
        return []
    q = " OR ".join(CATEGORIES[category]["keywords"])
    params = {"q": q, "pageSize": min(100,limit), "language":"en", "sortBy":"publishedAt", "apiKey": NEWSAPI_KEY}
    if country: params["q"] += f" AND ({country})"
    elif region: params["q"] += f" AND ({region})"
    try:
        r = requests.get("https://newsapi.org/v2/everything", params=params, timeout=20)
        r.raise_for_status()
        out=[]
        for a in r.json().get("articles", []):
            title=a.get("title","") or ""; desc=a.get("description","") or ""
            sc=_score(title, desc)
            out.append({"title":title,"summary":desc,"link":a.get("url"),
                        "published":a.get("publishedAt",""),
                        "source":a.get("source",{}).get("name",""),
                        **sc})
        return out[:limit]
    except Exception:
        return []

def fetch_news(category: str, country: Optional[str]=None, region: Optional[str]=None, limit:int=120):
    # Try NewsAPI first; always fall back to wide RSS with graceful padding.
    items = fetch_news_newsapi(category, country, region, limit)
    if len(items) < 10:
        items = fetch_news_rss(category, country, region, limit)
    return items
