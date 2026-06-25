from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest


class EdgeAnomalyDetector:
    """
    Simulated edge-side Isolation Forest detector.

    This runs close to the substation/simulator before telemetry is forwarded
    to the cloud pipeline.
    """

    def __init__(self) -> None:
        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42,
        )
        self.is_trained = False
        self.feature_names = [
            "voltage",
            "current",
            "temperature",
            "load",
            "frequency",
        ]

    def train_with_synthetic_baseline(self) -> None:
        normal_samples = []

        for _ in range(500):
            normal_samples.append(
                [
                    np.random.uniform(220, 235),
                    np.random.uniform(20, 38),
                    np.random.uniform(30, 55),
                    np.random.uniform(35, 75),
                    np.random.uniform(49.7, 50.3),
                ]
            )

        training_data = np.array(normal_samples)

        self.model.fit(training_data)
        self.is_trained = True

    def extract_features(self, telemetry: dict[str, Any]) -> np.ndarray:
        return np.array(
            [
                [
                    float(telemetry["voltage"]),
                    float(telemetry["current"]),
                    float(telemetry["temperature"]),
                    float(telemetry["load"]),
                    float(telemetry["frequency"]),
                ]
            ]
        )

    def analyze(self, telemetry: dict[str, Any]) -> dict[str, Any]:
        if not self.is_trained:
            self.train_with_synthetic_baseline()

        features = self.extract_features(telemetry)

        prediction = self.model.predict(features)[0]
        anomaly_score = float(self.model.decision_function(features)[0])

        edge_anomaly = prediction == -1

        return {
            **telemetry,
            "edge_anomaly": bool(edge_anomaly),
            "edge_anomaly_score": round(anomaly_score, 5),
            "edge_model": "IsolationForest-Edge",
            "edge_processed_at": datetime.utcnow().isoformat(),
        }


edge_detector = EdgeAnomalyDetector()