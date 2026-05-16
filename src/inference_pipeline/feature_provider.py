from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# make feature_pipeline imports work when running from inference_pipeline
sys.path.insert(0, str(Path(__file__).parent.parent / "feature_pipeline"))

from feature_engineering import compute_features, load_workouts  # type: ignore[import-not-found]

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


def _extract_phantom_features(
    featured: pd.DataFrame, exercise_name: str
) -> pd.DataFrame:
    """Extract the last phantom row for a given exercise and return feature columns."""
    exercise_rows = featured[featured["exercise_name"] == exercise_name]
    if len(exercise_rows) == 0:
        raise RuntimeError("Phantom row disappeared during feature computation")

    phantom_row = exercise_rows.tail(1)
    features = phantom_row[FEATURE_COLS].copy()

    for col in features.select_dtypes(include=["int64"]).columns:
        features[col] = features[col].astype("float64")

    return features


def build_features_for_next_session(
    exercise_name: str,
    history_csv: Path = Path("data/processed/workouts_exercises.csv"),
    planned_time: datetime | None = None,
) -> pd.DataFrame:
    if planned_time is None:
        planned_time = datetime.now(timezone.utc)

    results = build_features_for_batch(
        [exercise_name], history_csv=history_csv, planned_time=planned_time
    )
    if exercise_name not in results:
        raise ValueError(f"No history found for exercise: {exercise_name}")
    return results[exercise_name]


def build_features_for_batch(
    exercise_names: list[str],
    history_csv: Path = Path("data/processed/workouts_exercises.csv"),
    planned_time: datetime | None = None,
) -> dict[str, pd.DataFrame]:
    """Build features for multiple exercises in a single pass.

    This is much faster than calling build_features_for_next_session in a loop
    because compute_features is only executed once for the whole dataset.
    """
    if planned_time is None:
        planned_time = datetime.now(timezone.utc)

    if not history_csv.exists():
        raise FileNotFoundError(f"Workout history not found: {history_csv}")

    raw_df = pd.read_csv(history_csv)

    missing = [name for name in exercise_names if name not in raw_df["exercise_name"].values]
    if missing:
        raise ValueError(f"No history found for exercises: {', '.join(missing)}")

    iso_time = planned_time.replace(microsecond=0).isoformat()
    phantoms = pd.DataFrame(
        [
            {
                "workout_id": "",
                "workout_title": "",
                "start_time": iso_time,
                "end_time": iso_time,
                "exercise_name": name,
                "exercise_template_id": "",
                "superset_id": "",
                "total_sets": 0,
                "total_reps": 0,
                "total_volume_kg": 0.0,
                "avg_weight_kg": 0.0,
                "set_details": "[]",
            }
            for name in exercise_names
        ]
    )

    combined = pd.concat([raw_df, phantoms], ignore_index=True)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        temp_path = Path(f.name)
        combined.to_csv(temp_path, index=False)

    try:
        df = load_workouts(temp_path)
        featured = compute_features(df)
    finally:
        temp_path.unlink()

    return {
        name: _extract_phantom_features(featured, name)
        for name in exercise_names
    }
