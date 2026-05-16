from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

import pandas as pd

from inference import load_model, predict
from feature_provider import build_features_for_next_session
from feature_store import FeatureStoreCache, set_feature_store

FEATURE_STORE_DIR = Path("data/processed")


def list_exercises(history_csv: Path = Path("data/processed/workouts_exercises.csv")) -> pd.DataFrame:
    df = pd.read_csv(history_csv)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    latest = df.groupby("exercise_name")["start_time"].max().reset_index()
    latest = latest.sort_values("start_time", ascending=False).reset_index(drop=True)
    return latest


def get_last_session(exercise_name: str, history_csv: Path = Path("data/processed/workouts_exercises.csv")) -> pd.Series:
    df = pd.read_csv(history_csv)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    exercise_df = df[df["exercise_name"] == exercise_name]
    if len(exercise_df) == 0:
        raise ValueError(f"No history for {exercise_name}")
    return exercise_df.sort_values("start_time").iloc[-1]


def main() -> None:
    # initialize the feature store so build_features_for_next_session works
    store = FeatureStoreCache(FEATURE_STORE_DIR)
    set_feature_store(store)
    store.load()

    model = load_model()

    print("Loading workout history...")
    exercises = list_exercises().head(30)
    print(f"Showing latest {len(exercises)} exercises\n")

    print("Pick an exercise to predict next session volume:")
    for i, row in exercises.iterrows():
        date_str = row["start_time"].strftime("%Y-%m-%d")
        print(f"  {cast(int, i) + 1}. {row['exercise_name']} - last trained: {date_str}")

    while True:
        try:
            choice = input("\nEnter number: ").strip()
            idx = int(choice) - 1
            if idx < 0 or idx >= len(exercises):
                print("Invalid number. Try again.")
                continue
            break
        except ValueError:
            print("Please enter a number.")

    exercise_name = exercises.iloc[idx]["exercise_name"]

    try:
        features_df = build_features_for_next_session(exercise_name)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # check NaN
    if features_df.isnull().any().any():
        nan_cols = features_df.columns[features_df.isnull().any()].tolist()
        print(f"Not enough history for this exercise. Missing features: {', '.join(nan_cols)}")
        print("Need at least 3 sessions to compute all trend features.")
        sys.exit(1)

    try:
        preds = predict(model, features_df)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    predicted_volume = preds[0]

    # get last session stats
    last = get_last_session(exercise_name)
    last_sets = int(last["total_sets"])
    last_reps = int(last["total_reps"])
    last_weight = float(last["avg_weight_kg"])
    last_volume = float(last["total_volume_kg"])
    last_date = last["start_time"].strftime("%Y-%m-%d")

    # estimate average weight for next session
    # volume = weight x total_reps, so weight = volume / total_reps
    if last_reps > 0:
        estimated_weight = predicted_volume / last_reps
        reps_per_set = last_reps / last_sets if last_sets > 0 else 0
    else:
        estimated_weight = 0.0
        reps_per_set = 0

    # print results
    print(f"\n--- Last Session ({last_date}) ---")
    print(f"  Sets: {last_sets} | Reps: {last_reps} | Avg Weight: {last_weight:.1f} kg | Total Volume: {last_volume:.0f} kg")

    print("\n--- Predicted Next Session ---")
    print(f"  Predicted Volume: {predicted_volume:.0f} kg")
    if estimated_weight > 0 and reps_per_set > 0:
        print(f"  Estimated Weight: {estimated_weight:.1f} kg (assuming {last_sets} sets x ~{reps_per_set:.0f} reps)")

    print("\n--- Features Used ---")
    for col, val in features_df.iloc[0].items():
        if isinstance(val, float):
            print(f"  {col}: {val:.2f}")
        else:
            print(f"  {col}: {val}")


if __name__ == "__main__":
    main()
