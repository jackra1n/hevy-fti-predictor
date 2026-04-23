import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hevy_client import HevyClient


def save_raw_json(workouts: list[dict[str, Any]], output_dir: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"workouts_{timestamp}.json"
    raw_path.write_text(json.dumps(workouts, indent=2), encoding="utf-8")
    print(f"Saved raw JSON: {raw_path}")
    return raw_path


def flatten_workouts_to_csv(workouts: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for w in workouts:
        workout_id = w.get("id")
        workout_title = w.get("title", "")
        start_time = w.get("start_time", "")
        end_time = w.get("end_time", "")

        for ex in w.get("exercises", []):
            exercise_name = ex.get("title", "")
            exercise_template_id = ex.get("exercise_template_id", "")
            superset_id = ex.get("superset_id")

            total_volume = 0.0
            total_sets = 0
            total_reps = 0
            set_details = []

            for s in ex.get("sets", []):
                weight = s.get("weight_kg") or 0
                reps = s.get("reps") or 0
                set_volume = weight * reps
                total_volume += set_volume
                total_sets += 1
                total_reps += reps
                set_details.append({
                    "set_type": s.get("type", ""),
                    "weight_kg": weight,
                    "reps": reps,
                    "rpe": s.get("rpe"),
                })

            rows.append({
                "workout_id": workout_id,
                "workout_title": workout_title,
                "start_time": start_time,
                "end_time": end_time,
                "exercise_name": exercise_name,
                "exercise_template_id": exercise_template_id,
                "superset_id": superset_id,
                "total_sets": total_sets,
                "total_reps": total_reps,
                "total_volume_kg": round(total_volume, 2),
                "avg_weight_kg": round(total_volume / total_reps, 2) if total_reps > 0 else 0,
                "set_details": json.dumps(set_details),
            })

    return pd.DataFrame(rows)


def main() -> None:
    client = HevyClient()
    print("Fetching all workouts from Hevy API...")
    workouts = client.fetch_all_workouts(page_size=10)
    print(f"Fetched {len(workouts)} workouts.")

    if not workouts:
        print("No workouts found.")
        return

    # Directories
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Save raw JSON
    save_raw_json(workouts, raw_dir)

    # Flatten to CSV
    df = flatten_workouts_to_csv(workouts)
    csv_path = processed_dir / "workouts_exercises.csv"
    df.to_csv(csv_path, index=False)
    print(f"Saved CSV: {csv_path} ({len(df)} exercise records)")

    # Quick stats
    print("\n--- Quick Stats ---")
    print(f"Workouts: {len(workouts)}")
    print(f"Unique exercises: {df['exercise_name'].nunique()}")
    print(f"Date range: {df['start_time'].min()} to {df['start_time'].max()}")
    print("\nTop 5 exercises by frequency:")
    print(df["exercise_name"].value_counts().head())


if __name__ == "__main__":
    main()
