import json
import os
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

import dagshub
import mlflow
import pandas as pd
from dotenv import load_dotenv
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib

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

CATEGORICAL_COLS = ["muscle_group", "day_of_week"]
NUMERICAL_COLS = [c for c in FEATURE_COLS if c not in CATEGORICAL_COLS]

TARGET_COL = "total_volume_kg"


def find_latest_features(features_dir: Path) -> Path:
    files = sorted(features_dir.glob("features_*.csv"))
    if not files:
        raise FileNotFoundError(f"No features_*.csv found in {features_dir}")
    return files[-1]


def load_and_prepare(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[FEATURE_COLS + [TARGET_COL]]
    df = df.dropna()
    return df


def evaluate(model: Pipeline, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
    y_pred = model.predict(X_test)
    return {
        "test_rmse": round(float(mean_squared_error(y_test, y_pred) ** 0.5), 4),
        "test_mae": round(float(mean_absolute_error(y_test, y_pred)), 4),
        "test_r2": round(float(r2_score(y_test, y_pred)), 4),
    }


def save_artifacts(model: Pipeline, metrics: dict[str, float], models_dir: Path) -> None:
    models_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    model_path = models_dir / f"model_{timestamp}.pkl"
    joblib.dump(model, model_path)
    print(f"Saved model: {model_path}")

    metrics_path = models_dir / f"metrics_{timestamp}.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(f"Saved metrics: {metrics_path}")


def _setup_mlflow() -> bool:
    token = os.environ.get("DAGSHUB_TOKEN", "")
    if not token:
        return False

    dagshub.init(  # type: ignore[reportPrivateImportUsage]
        repo_owner=os.environ["DAGSHUB_REPO_OWNER"],
        repo_name=os.environ["DAGSHUB_REPO_NAME"],
    )
    os.environ["MLFLOW_TRACKING_USERNAME"] = os.environ["DAGSHUB_REPO_OWNER"]
    os.environ["MLFLOW_TRACKING_PASSWORD"] = token

    mlflow.set_experiment("hevy-fti-predictor")
    mlflow.sklearn.autolog(log_models=False)  # type: ignore[reportPrivateImportUsage]
    return True


def main() -> None:
    load_dotenv()
    use_mlflow = _setup_mlflow()

    features_path = find_latest_features(Path("data/processed"))
    print(f"Loading features from {features_path}")
    df = load_and_prepare(features_path)
    print(f"Loaded {len(df)} complete records after dropping NaN rows.")

    X = df[FEATURE_COLS].copy()
    y = df[TARGET_COL]

    # convert integer columns to float64 to avoid MLflow schema enforcement warnings
    for col in X.select_dtypes(include=["int64"]).columns:
        X[col] = X[col].astype("float64")

    X_train, X_test, y_train, y_test = cast(
        tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series],
        train_test_split(X, y, test_size=0.2, shuffle=False),
    )
    print(
        f"Train: {len(X_train)} samples, Test: {len(X_test)} samples "
        f"(time-based split, test=last 20%)"
    )

    preprocessor = ColumnTransformer(
        [
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
            ("num", StandardScaler(), NUMERICAL_COLS),
        ],
        remainder="drop",
    )

    pipeline = Pipeline(
        [
            ("preprocessor", preprocessor),
            ("model", RandomForestRegressor(n_estimators=100, random_state=42)),
        ]
    )

    run_ctx = mlflow.start_run() if use_mlflow else nullcontext()
    with run_ctx:
        print("Training RandomForestRegressor...")
        pipeline.fit(X_train, y_train)

        metrics = evaluate(pipeline, X_test, y_test)
        print("\n--- Evaluation ---")
        print(f"RMSE: {metrics['test_rmse']:.2f} kg")
        print(f"MAE:  {metrics['test_mae']:.2f} kg")
        print(f"R²:   {metrics['test_r2']:.4f}")

        if use_mlflow:
            mlflow.log_metrics(metrics)

        feature_names = pipeline.named_steps["preprocessor"].get_feature_names_out()
        importances = pipeline.named_steps["model"].feature_importances_
        importance_df = (
            pd.DataFrame({"feature": feature_names, "importance": importances})
            .sort_values("importance", ascending=False)
            .head(10)
        )
        print("\nTop 10 feature importances:")
        print(importance_df.to_string(index=False))

        save_artifacts(pipeline, metrics, Path("models"))


if __name__ == "__main__":
    main()
