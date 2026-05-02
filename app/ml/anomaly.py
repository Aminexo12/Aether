from __future__ import annotations

import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.data.models import Flight

_MODEL_PATH = Path(__file__).parent / "artifacts" / "anomaly_model.joblib"


def _features(flights: list[Flight]) -> tuple[np.ndarray, list[Flight]]:
    """Extract numeric features from a list of flights. Drops flights with missing data."""
    rows, valid = [], []
    for f in flights:
        if f.velocity is None or f.baro_altitude is None or f.vertical_rate is None:
            continue
        rows.append([f.velocity, f.baro_altitude, f.vertical_rate])
        valid.append(f)
    return np.array(rows, dtype=float), valid


def train(flights: list[Flight], contamination: float = 0.05) -> IsolationForest:
    """Train an Isolation Forest on a snapshot of flights and save the model."""
    X, _ = _features(flights)
    model = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
    model.fit(X)
    _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, _MODEL_PATH)
    return model


def load_model() -> IsolationForest | None:
    if _MODEL_PATH.exists():
        return joblib.load(_MODEL_PATH)
    return None


def detect(flights: list[Flight], top_k: int = 10) -> list[dict]:
    """Score flights and return the top_k most anomalous ones."""
    model = load_model()
    if model is None:
        return []

    X, valid = _features(flights)
    if len(X) == 0:
        return []

    # score_samples: lower = more anomalous
    scores = model.score_samples(X)
    ranked = sorted(zip(scores, valid), key=lambda x: x[0])

    results = []
    for score, f in ranked[:top_k]:
        results.append({
            "icao24": f.icao24,
            "callsign": f.callsign or f.icao24,
            "country": f.origin_country,
            "velocity_kmh": round(f.velocity * 3.6, 0) if f.velocity else None,
            "altitude_m": f.baro_altitude,
            "vertical_rate": f.vertical_rate,
            "anomaly_score": round(float(score), 4),
        })
    return results
