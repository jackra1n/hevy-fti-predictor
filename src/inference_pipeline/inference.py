from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline


def find_latest_model(models_dir: Path = Path("models")) -> Path:
    files = sorted(models_dir.glob("model_*.pkl"))
    if not files:
        raise FileNotFoundError(f"No model_*.pkl found in {models_dir}")
    return files[-1]


def load_model(model_path: Path | None = None) -> Pipeline:
    if model_path is None:
        model_path = find_latest_model()
    print(f"Loading model: {model_path}")
    model = joblib.load(model_path)
    if not isinstance(model, Pipeline):
        raise TypeError(f"Expected sklearn Pipeline, got {type(model)}")
    return model


def predict(model: Pipeline, features_df: pd.DataFrame) -> list[float]:
    if features_df.isnull().any().any():
        nan_cols = features_df.columns[features_df.isnull().any()].tolist()
        raise ValueError(f"Features contain NaN values in columns: {nan_cols}")
    preds = model.predict(features_df)
    return [float(p) for p in preds]
