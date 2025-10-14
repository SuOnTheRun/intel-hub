import os

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "").strip()

REDDIT = {
    "client_id": os.getenv("REDDIT_CLIENT_ID", "").strip(),
    "client_secret": os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
    "username": os.getenv("REDDIT_USERNAME", "").strip(),
    "password": os.getenv("REDDIT_PASSWORD", "").strip(),
    "user_agent": os.getenv("REDDIT_USER_AGENT", "blis-intel-hub/1.0").strip(),
}

POLYGON_KEY = os.getenv("POLYGON_KEY", "").strip()
