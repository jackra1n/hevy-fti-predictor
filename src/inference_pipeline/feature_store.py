from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import pandas as pd


class FeatureStoreCache:
    """thread-safe loader for pre-computed feature CSV from the feature store

    loads the latest ``features_*.csv`` from ``processed_dir`` into memory,
    parses dates, and pre-computes daily aggregates for fast phantom-row
    feature extraction
    """

    def __init__(self, processed_dir: Path) -> None:
        self._processed_dir = processed_dir
        self._df: pd.DataFrame | None = None
        self._muscle_daily: pd.DataFrame | None = None
        self._daily_total: pd.DataFrame | None = None
        self._workout_dates: list[Any] = []
        self._lock = threading.Lock()
        self._ready = threading.Event()

    def load(self) -> None:
        """find the latest feature CSV, load it, and pre-compute aggregates
        called once in a background thread at module import time
        """
        with self._lock:
            if self._df is not None:
                self._ready.set()
                return

            files = sorted(self._processed_dir.glob("features_*.csv"))
            if not files:
                raise FileNotFoundError(
                    f"No features_*.csv found in {self._processed_dir}"
                )

            latest = files[-1]
            print(f"Loading feature store: {latest}")
            self._df = pd.read_csv(latest)
            self._df["start_time"] = pd.to_datetime(self._df["start_time"], utc=True)
            self._df["end_time"] = pd.to_datetime(self._df["end_time"], utc=True)
            self._df["workout_date"] = pd.to_datetime(
                self._df["start_time"], utc=True
            ).dt.date

            self._df = self._df.sort_values("start_time").reset_index(drop=True)

            self._muscle_daily = (
                self._df.groupby(["workout_date", "muscle_group"])["total_volume_kg"]
                .sum()
                .reset_index()
            )
            self._daily_total = (
                self._df.groupby("workout_date")["total_volume_kg"]
                .sum()
                .reset_index()
            )
            self._workout_dates = sorted(self._df["workout_date"].unique())

            print(
                f"Feature store loaded: {len(self._df)} rows, "
                f"{self._df['exercise_name'].nunique()} exercises"
            )
            self._ready.set()

    def get(self) -> pd.DataFrame:
        self._ready.wait()
        if self._df is None:
            raise RuntimeError("Feature store failed to load")
        return self._df

    def get_muscle_daily(self) -> pd.DataFrame:
        self._ready.wait()
        if self._muscle_daily is None:
            raise RuntimeError("Feature store failed to load")
        return self._muscle_daily

    def get_daily_total(self) -> pd.DataFrame:
        self._ready.wait()
        if self._daily_total is None:
            raise RuntimeError("Feature store failed to load")
        return self._daily_total

    def get_workout_dates(self) -> list[Any]:
        self._ready.wait()
        return self._workout_dates

    def is_ready(self) -> bool:
        return self._ready.is_set()


class _StoreHolder:
    _store: FeatureStoreCache | None = None


def set_feature_store(store: FeatureStoreCache) -> None:
    _StoreHolder._store = store


def get_feature_store() -> FeatureStoreCache:
    if _StoreHolder._store is None:
        raise RuntimeError(
            "Feature store not initialized. Call set_feature_store() first."
        )
    return _StoreHolder._store
