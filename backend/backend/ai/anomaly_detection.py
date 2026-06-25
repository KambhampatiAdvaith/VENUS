import numpy as np
from sklearn.ensemble import IsolationForest


def train_isolation_forest(features):
    model = IsolationForest(
        n_estimators=150,
        contamination=0.15,
        random_state=42,
    )

    model.fit(features)

    return model


def calculate_anomaly_score(model, features):
    decision_scores = model.decision_function(features)
    predictions = model.predict(features)

    results = []

    for decision_score, prediction in zip(decision_scores, predictions):
        anomaly = prediction == -1

        risk_score = 1 / (1 + np.exp(5 * decision_score))
        risk_score = round(float(risk_score), 4)

        results.append(
            {
                "anomaly": bool(anomaly),
                "score": risk_score,
            }
        )

    return results