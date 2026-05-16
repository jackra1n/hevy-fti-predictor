from __future__ import annotations

import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from inference_pipeline.feature_provider import build_features_for_next_session
from inference_pipeline.inference import predict

_MODEL: Any | None = None
_MODEL_LOCK = threading.Lock()
HISTORY_CSV = Path(os.environ.get("HISTORY_CSV_PATH", "data/processed/workouts_exercises.csv"))
MODEL_URI = os.environ.get("MLFLOW_MODEL_URI", "models:/hevy-fti-model/latest")


def _list_exercises(history_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(history_csv)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    latest = df.groupby("exercise_name")["start_time"].max().reset_index()
    latest = latest.sort_values("start_time", ascending=False).reset_index(drop=True)
    return latest


def _get_last_session(exercise_name: str, history_csv: Path) -> pd.Series:
    df = pd.read_csv(history_csv)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    exercise_df = df[df["exercise_name"] == exercise_name]
    if len(exercise_df) == 0:
        raise ValueError(f"No history for {exercise_name}")
    return exercise_df.sort_values("start_time").iloc[-1]


def _setup_mlflow() -> None:
    token = os.environ.get("DAGSHUB_TOKEN", "")
    if not token:
        raise RuntimeError("DAGSHUB_TOKEN not set")

    owner = os.environ["DAGSHUB_REPO_OWNER"]
    repo = os.environ["DAGSHUB_REPO_NAME"]

    os.environ["MLFLOW_TRACKING_URI"] = f"https://dagshub.com/{owner}/{repo}.mlflow"
    os.environ["MLFLOW_TRACKING_USERNAME"] = owner
    os.environ["MLFLOW_TRACKING_PASSWORD"] = token


def _load_model_once() -> Any:
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    with _MODEL_LOCK:
        if _MODEL is not None:
            return _MODEL
        _setup_mlflow()
        print(f"Loading model from MLflow registry: {MODEL_URI}")
        _MODEL = mlflow.sklearn.load_model(MODEL_URI)  # type: ignore[reportPrivateImportUsage]
        print("Model loaded successfully")
        return _MODEL


app = FastAPI(title="Hevy FTI Predictor")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/exercises")
def exercises() -> list[dict[str, Any]]:
    df = _list_exercises(HISTORY_CSV)
    return [
        {"name": row["exercise_name"], "last_trained": row["start_time"].strftime("%Y-%m-%d")}
        for _, row in df.iterrows()
    ]


class PredictRequest(BaseModel):
    exercise_name: str
    planned_time: datetime | None = None


class PredictResponse(BaseModel):
    exercise_name: str
    predicted_volume_kg: float
    estimated_weight_kg: float | None
    estimated_sets: int | None
    estimated_reps_per_set: float | None
    last_session_date: str
    last_session_volume_kg: float
    features_used: dict[str, Any]
    model_version: str


@app.post("/predict", response_model=PredictResponse)
def predict_endpoint(req: PredictRequest) -> PredictResponse:
    model = _load_model_once()

    try:
        features_df = build_features_for_next_session(
            req.exercise_name, HISTORY_CSV, req.planned_time
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if features_df.isnull().any().any():
        nan_cols = features_df.columns[features_df.isnull().any()].tolist()
        raise HTTPException(
            status_code=400,
            detail=f"Not enough history for this exercise. Missing features: {', '.join(nan_cols)}",
        )

    preds = predict(model, features_df)
    predicted_volume = float(preds[0])

    try:
        last = _get_last_session(req.exercise_name, HISTORY_CSV)
    except ValueError:
        last = None

    if last is not None:
        last_sets = int(last["total_sets"])
        last_reps = int(last["total_reps"])
        last_volume = float(last["total_volume_kg"])
        last_date = last["start_time"].strftime("%Y-%m-%d")

        if last_reps > 0:
            estimated_weight = predicted_volume / last_reps
            reps_per_set = last_reps / last_sets if last_sets > 0 else 0
        else:
            estimated_weight = None
            reps_per_set = None
    else:
        last_sets = None
        last_reps = None
        last_volume = 0.0
        last_date = ""
        estimated_weight = None
        reps_per_set = None

    features_dict: dict[str, Any] = {
        str(col): float(val) if isinstance(val, (int, float)) else str(val)
        for col, val in features_df.iloc[0].items()
    }

    return PredictResponse(
        exercise_name=req.exercise_name,
        predicted_volume_kg=round(predicted_volume, 1),
        estimated_weight_kg=round(estimated_weight, 1) if estimated_weight else None,
        estimated_sets=last_sets,
        estimated_reps_per_set=round(reps_per_set, 1) if reps_per_set else None,
        last_session_date=last_date,
        last_session_volume_kg=round(last_volume, 1),
        features_used=features_dict,
        model_version="hevy-fti-model:latest",
    )
