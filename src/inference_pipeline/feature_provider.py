from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd

try:
    from .feature_store import get_feature_store
except ImportError:
    from feature_store import get_feature_store  # type: ignore[no-redef]

FEATURE_COLS = [
    "muscle_group",
    "rolling_7d_volume_same_muscle",
    "days_since_last_exercise",
    "prev_session_volume",
    "prev_session_avg_weight",
    "prev_session_total_sets",
    "prev_session_total_reps",
    "rolling_3s_avg_volume",
    "rolling_5s_avg_volume",
    "volume_trend",
    "rolling_7d_total_volume",
    "rolling_28d_total_volume",
    "workouts_last_7d",
    "workouts_last_28d",
    "day_of_week",
    "hour_of_day",
]


def _rolling_muscle_volume(
    muscle_daily: pd.DataFrame,
    muscle: str | None,
    planned_date: datetime,
    days: int = 7,
) -> float:
    if muscle is None:
        return 0.0
    window_start = planned_date - timedelta(days=days)
    mask = (
        (muscle_daily["muscle_group"] == muscle)
        & (muscle_daily["workout_date"] > window_start.date())
        & (muscle_daily["workout_date"] < planned_date.date())
    )
    return float(muscle_daily.loc[mask, "total_volume_kg"].sum())  # type: ignore[no-any-return]


def _rolling_global_volume(
    daily_total: pd.DataFrame,
    planned_date: datetime,
    days: int,
) -> float:
    window_start = planned_date - timedelta(days=days)
    mask = (daily_total["workout_date"] > window_start.date()) & (
        daily_total["workout_date"] < planned_date.date()
    )
    return float(daily_total.loc[mask, "total_volume_kg"].sum())  # type: ignore[no-any-return]


def _workout_count_last_n_days(
    workout_dates: list[Any],
    planned_date: datetime,
    days: int,
) -> int:
    window_start = planned_date - timedelta(days=days)
    return sum(
        1
        for d in workout_dates
        if d > window_start.date() and d < planned_date.date()
    )


def _compute_phantom_features(
    store_df: pd.DataFrame,
    muscle_daily: pd.DataFrame,
    daily_total: pd.DataFrame,
    workout_dates: list[Any],
    exercise_name: str,
    planned_time: datetime,
) -> pd.DataFrame:
    exercise_rows = store_df[store_df["exercise_name"] == exercise_name]
    if len(exercise_rows) == 0:
        raise ValueError(f"No history found for exercise: {exercise_name}")

    last = exercise_rows.iloc[-1]
    planned_date = planned_time.replace(tzinfo=timezone.utc)
    muscle = last["muscle_group"]

    return pd.DataFrame(
        [
            {
                "muscle_group": muscle,
                "rolling_7d_volume_same_muscle": _rolling_muscle_volume(
                    muscle_daily, muscle, planned_date
                ),
                "days_since_last_exercise": (
                    planned_date - pd.to_datetime(last["start_time"], utc=True)
                ).total_seconds()
                / 86_400,
                "prev_session_volume": float(last["total_volume_kg"]),
                "prev_session_avg_weight": float(last["avg_weight_kg"]),
                "prev_session_total_sets": int(last["total_sets"]),
                "prev_session_total_reps": int(last["total_reps"]),
                "rolling_3s_avg_volume": float(
                    exercise_rows["total_volume_kg"].tail(3).mean()
                ),
                "rolling_5s_avg_volume": float(
                    exercise_rows["total_volume_kg"].tail(5).mean()
                ),
                "volume_trend": float(
                    exercise_rows["total_volume_kg"].diff().tail(3).mean()
                ),
                "rolling_7d_total_volume": _rolling_global_volume(
                    daily_total, planned_date, 7
                ),
                "rolling_28d_total_volume": _rolling_global_volume(
                    daily_total, planned_date, 28
                ),
                "workouts_last_7d": _workout_count_last_n_days(
                    workout_dates, planned_date, 7
                ),
                "workouts_last_28d": _workout_count_last_n_days(
                    workout_dates, planned_date, 28
                ),
                "day_of_week": planned_date.weekday(),
                "hour_of_day": planned_date.hour,
            }
        ]
    )[FEATURE_COLS]


def build_features_for_next_session(
    exercise_name: str,
    planned_time: datetime | None = None,
) -> pd.DataFrame:
    if planned_time is None:
        planned_time = datetime.now(timezone.utc)

    results = build_features_for_batch(
        [exercise_name], planned_time=planned_time
    )
    if exercise_name not in results:
        raise ValueError(f"No history found for exercise: {exercise_name}")
    return results[exercise_name]


def build_features_for_batch(
    exercise_names: list[str],
    planned_time: datetime | None = None,
) -> dict[str, pd.DataFrame]:
    if planned_time is None:
        planned_time = datetime.now(timezone.utc)

    store = get_feature_store()

    store_df = store.get()
    muscle_daily = store.get_muscle_daily()
    daily_total = store.get_daily_total()
    workout_dates = store.get_workout_dates()

    missing = [
        name for name in exercise_names if name not in store_df["exercise_name"].values
    ]
    if missing:
        raise ValueError(f"No history found for exercises: {', '.join(missing)}")

    return {
        name: _compute_phantom_features(
            store_df,
            muscle_daily,
            daily_total,
            workout_dates,
            name,
            planned_time,
        )
        for name in exercise_names
    }
