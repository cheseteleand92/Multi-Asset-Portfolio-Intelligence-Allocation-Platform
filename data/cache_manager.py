"""Simple parquet cache manager for market data snapshots."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class CacheManager:
    """Manage local cache files for data requests."""

    def __init__(self, cache_dir: str = "./.cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, df: pd.DataFrame) -> Path:
        path = self.cache_dir / f"{key}.parquet"
        df.to_parquet(path)
        return path

    def get(self, key: str) -> pd.DataFrame:
        path = self.cache_dir / f"{key}.parquet"
        if not path.exists():
            raise FileNotFoundError(key)
        return pd.read_parquet(path)
