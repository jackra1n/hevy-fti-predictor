from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import pandas as pd

from exercise_mapping import get_muscle_group


def load_workouts(csv_path: Path) -> pd.DataFrame:
    """Load and normalise the raw workout-exercise CSV."""
    df = pd.read_csv(csv_path)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["end_time"] = pd.to_datetime(df["end_time"], utc=True)
    df["workout_date"] = df["start_time"].dt.date
    df["muscle_group"] = df["exercise_name"].apply(get_muscle_group)
    return df.sort_values("start_time").reset_index(drop=True)


def _rolling_mean_shifted(series: pd.Series, window: int) -> pd.Series:  # type: ignore[no-untyped-def]
    """Rolling mean of the *previous* values in a Series."""
    return series.shift(1).rolling(window=window, min_periods=1).mean()


def _volume_trend(series: pd.Series) -> pd.Series:  # type: ignore[no-untyped-def]
    """Mean first-difference of the *previous* values in a Series."""
    return series.shift(1).diff().rolling(window=3, min_periods=1).mean()


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure chronological order
    df = df.sort_values("start_time").reset_index(drop=True)

    # ------------------------------------------------------------------
    # 1. Rolling 7-day total volume per muscle group
    # ------------------------------------------------------------------
    muscle_daily = (
        df.groupby(["workout_date", "muscle_group"])["total_volume_kg"]
        .sum()
        .reset_index()
        .rename(columns={"total_volume_kg": "daily_muscle_volume"})
    )

    def _rolling_muscle_volume(row: pd.Series) -> float:
        muscle = cast(str | None, row["muscle_group"])
        if muscle is None:
            return 0.0
        current_date = cast(date, row["workout_date"])
        window_start = current_date - timedelta(days=7)
        mask = (
            (muscle_daily["muscle_group"] == muscle)
            & (muscle_daily["workout_date"] > window_start)
            & (muscle_daily["workout_date"] < current_date)
        )
        return float(muscle_daily.loc[mask, "daily_muscle_volume"].sum())

    df["rolling_7d_volume_same_muscle"] = df.apply(_rolling_muscle_volume, axis=1)

    # ------------------------------------------------------------------
    # 2. Days since last exercise + historical progression
    # ------------------------------------------------------------------
    df["prev_session_start_time"] = df.groupby("exercise_name")["start_time"].shift(1)
    df["days_since_last_exercise"] = (
        df["start_time"] - df["prev_session_start_time"]
    ).dt.total_seconds() / 86_400
    df["prev_session_volume"] = df.groupby("exercise_name")["total_volume_kg"].shift(1)
    df["prev_session_avg_weight"] = df.groupby("exercise_name")["avg_weight_kg"].shift(
        1
    )
    df["prev_session_total_sets"] = df.groupby("exercise_name")["total_sets"].shift(1)
    df["prev_session_total_reps"] = df.groupby("exercise_name")["total_reps"].shift(1)

    # Rolling averages using transform (avoids MultiIndex type-checker pain)
    df["rolling_3s_avg_volume"] = df.groupby("exercise_name")[
        "total_volume_kg"
    ].transform(lambda x: _rolling_mean_shifted(x, 3))
    df["rolling_5s_avg_volume"] = df.groupby("exercise_name")[
        "total_volume_kg"
    ].transform(lambda x: _rolling_mean_shifted(x, 5))
    df["volume_trend"] = df.groupby("exercise_name")["total_volume_kg"].transform(
        _volume_trend
    )

    # ------------------------------------------------------------------
    # 3. Global workload indicators
    # ------------------------------------------------------------------
    daily_total = df.groupby("workout_date")["total_volume_kg"].sum().reset_index()
    daily_total = daily_total.rename(columns={"total_volume_kg": "daily_total_volume"})

    def _rolling_global_volume(row: pd.Series, days: int) -> float:
        current_date = cast(date, row["workout_date"])
        window_start = current_date - timedelta(days=days)
        mask = (daily_total["workout_date"] > window_start) & (
            daily_total["workout_date"] < current_date
        )
        return float(daily_total.loc[mask, "daily_total_volume"].sum())

    df["rolling_7d_total_volume"] = df.apply(
        lambda r: _rolling_global_volume(r, 7), axis=1
    )
    df["rolling_28d_total_volume"] = df.apply(
        lambda r: _rolling_global_volume(r, 28), axis=1
    )

    # Number of workouts in the last N days
    workout_dates = pd.Series(df["workout_date"].unique()).sort_values()

    def _workouts_in_last_n_days(row: pd.Series, days: int) -> int:
        current_date = cast(date, row["workout_date"])
        window_start = current_date - timedelta(days=days)
        mask = (workout_dates > window_start) & (workout_dates < current_date)
        return int(mask.sum())

    df["workouts_last_7d"] = df.apply(lambda r: _workouts_in_last_n_days(r, 7), axis=1)
    df["workouts_last_28d"] = df.apply(
        lambda r: _workouts_in_last_n_days(r, 28), axis=1
    )

    # ------------------------------------------------------------------
    # 4. Temporal features
    # ------------------------------------------------------------------
    df["day_of_week"] = df["start_time"].dt.dayofweek  # Monday=0
    df["hour_of_day"] = df["start_time"].dt.hour

    return df


def save_feature_store(df: pd.DataFrame, output_dir: Path) -> Path:
    """Save the feature DataFrame as a versioned CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"features_{timestamp}.csv"
    df.to_csv(path, index=False)
    print(f"Saved feature store: {path}")
    return path


def main() -> None:
    raw_csv = Path("data/processed/workouts_exercises.csv")
    if not raw_csv.exists():
        raise FileNotFoundError(f"Raw CSV not found: {raw_csv}")

    print("Loading workouts...")
    df = load_workouts(raw_csv)
    print(f"Loaded {len(df)} exercise records.")

    print("Computing features...")
    df = compute_features(df)

    # Save
    _ = save_feature_store(df, Path("data/processed"))

    # Quick sanity check
    print("\n--- Feature Summary ---")
    print(f"Records: {len(df)}")
    print(f"Features: {len(df.columns)}")
    print(f"Muscle groups covered: {df['muscle_group'].nunique()}")
    print(f"Missing muscle group mappings: {df['muscle_group'].isna().sum()}")
    print("\nSample features:")
    print(
        df[
            [
                "exercise_name",
                "start_time",
                "total_volume_kg",
                "rolling_7d_volume_same_muscle",
                "days_since_last_exercise",
                "prev_session_volume",
                "rolling_3s_avg_volume",
                "rolling_7d_total_volume",
                "workouts_last_7d",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
