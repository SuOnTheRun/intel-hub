import os
import pandas as pd
from functools import wraps
from diskcache import Cache
from datetime import datetime

_cache = Cache(directory=".cache")

def ttl_cache(ttl_seconds: int = 600):
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (fn.__name__, str(args), str(sorted(kwargs.items())))
            if key in _cache:
                return _cache[key]
            val = fn(*args, **kwargs)
            _cache.set(key, val, expire=ttl_seconds)
            return val
        return wrapper
    return deco

def cache_df(name: str, df: pd.DataFrame):
    os.makedirs("snapshots", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    p = f"snapshots/{name}_{ts}.parquet"
    try:
        df.to_parquet(p, index=False)
    except Exception:
        df.to_csv(p.replace(".parquet",".csv"), index=False)
