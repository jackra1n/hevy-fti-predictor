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

from inference_pipeline.feature_provider import (
    build_features_for_batch,
    build_features_for_next_session,
)
from inference_pipeline.feature_store import FeatureStoreCache, set_feature_store
from inference_pipeline.inference import predict

PROCESSED_DIR = Path(os.environ.get("PROCESSED_DIR", "data/processed"))
MODEL_URI = os.environ.get("MLFLOW_MODEL_URI", "models:/hevy-fti-model/latest")

_feature_store = FeatureStoreCache(PROCESSED_DIR)
set_feature_store(_feature_store)


def _list_exercises() -> pd.DataFrame:
    df = _feature_store.get()
    latest = df.groupby("exercise_name")["start_time"].max().reset_index()
    latest = latest.sort_values("start_time", ascending=False).reset_index(drop=True)
    return latest


def _get_last_session(exercise_name: str) -> pd.Series | None:
    df = _feature_store.get()
    exercise_df = df[df["exercise_name"] == exercise_name]
    if len(exercise_df) == 0:
        return None
    return exercise_df.iloc[-1]


def _setup_mlflow() -> None:
    token = os.environ.get("DAGSHUB_TOKEN", "")
    if not token:
        raise RuntimeError("DAGSHUB_TOKEN not set")

    owner = os.environ["DAGSHUB_REPO_OWNER"]
    repo = os.environ["DAGSHUB_REPO_NAME"]

    os.environ["MLFLOW_TRACKING_URI"] = f"https://dagshub.com/{owner}/{repo}.mlflow"
    os.environ["MLFLOW_TRACKING_USERNAME"] = owner
    os.environ["MLFLOW_TRACKING_PASSWORD"] = token


class ModelProvider:
    """thread-safe model loader from MLflow registry"""

    def __init__(self, model_uri: str) -> None:
        self._model_uri = model_uri
        self._model: Any | None = None
        self._lock = threading.Lock()
        self._ready = threading.Event()

    def load(self) -> None:
        """download and cache the model. called once in a background thread"""
        with self._lock:
            if self._model is not None:
                self._ready.set()
                return
            _setup_mlflow()
            print(f"Loading model from MLflow registry: {self._model_uri}")
            self._model = mlflow.sklearn.load_model(self._model_uri)  # type: ignore[reportPrivateImportUsage]
            print("Model loaded successfully")
            self._ready.set()

    def get(self) -> Any:
        """return the cached model, blocking until it is ready"""
        self._ready.wait()
        return self._model

    def is_ready(self) -> bool:
        return self._ready.is_set()


_model_provider = ModelProvider(MODEL_URI)

# start downloading the model and loading the feature store in background
# threads immediately on import.  with --min-instances 1 the container
# stays warm and everything is ready when the first request arrives.
threading.Thread(target=_model_provider.load, daemon=True).start()
threading.Thread(target=_feature_store.load, daemon=True).start()

app = FastAPI(title="Hevy FTI Predictor")


def _run_prediction(
    exercise_name: str,
    features_df: pd.DataFrame,
) -> dict[str, Any]:
    model = _model_provider.get()

    if features_df.isnull().any().any():
        nan_cols = features_df.columns[features_df.isnull().any()].tolist()
        raise HTTPException(
            status_code=400,
            detail=f"Not enough history for this exercise. Missing features: {', '.join(nan_cols)}",
        )

    preds = predict(model, features_df)
    predicted_volume = float(preds[0])

    last = _get_last_session(exercise_name)

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

    return {
        "exercise_name": exercise_name,
        "predicted_volume_kg": round(predicted_volume, 1),
        "estimated_weight_kg": round(estimated_weight, 1) if estimated_weight else None,
        "estimated_sets": last_sets,
        "estimated_reps_per_set": round(reps_per_set, 1) if reps_per_set else None,
        "last_session_date": last_date,
        "last_session_volume_kg": round(last_volume, 1),
        "features_used": features_dict,
        "model_version": "hevy-fti-model:latest",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "model_ready": _model_provider.is_ready(),
        "feature_store_ready": _feature_store.is_ready(),
    }


@app.get("/exercises")
def exercises() -> list[dict[str, Any]]:
    df = _list_exercises()
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
    try:
        features_df = build_features_for_next_session(
            req.exercise_name, req.planned_time
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    result = _run_prediction(req.exercise_name, features_df)
    return PredictResponse(**result)


class BatchPredictRequest(BaseModel):
    exercises: list[str]
    planned_time: datetime | None = None


class BatchPredictResponse(BaseModel):
    predictions: list[PredictResponse]


@app.post("/predict/batch", response_model=BatchPredictResponse)
def batch_predict_endpoint(req: BatchPredictRequest) -> BatchPredictResponse:
    if not req.exercises:
        raise HTTPException(status_code=400, detail="No exercises provided")

    try:
        all_features = build_features_for_batch(
            req.exercises, req.planned_time
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    results: list[PredictResponse] = []
    errors: list[str] = []

    for name in req.exercises:
        try:
            features_df = all_features[name]
            result = _run_prediction(name, features_df)
            results.append(PredictResponse(**result))
        except HTTPException as exc:
            errors.append(f"{name}: {exc.detail}")

    if errors and not results:
        raise HTTPException(status_code=400, detail="; ".join(errors))

    return BatchPredictResponse(predictions=results)
