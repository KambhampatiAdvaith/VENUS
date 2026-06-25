from pathlib import Path

import joblib
from sqlalchemy import text

from backend.ai.anomaly_detection import calculate_anomaly_score
from backend.api.database import get_engine
from backend.ai.feature_engineering import (
    FEATURE_COLUMNS,
    load_latest_telemetry_per_substation,
)


MODEL_DIR = Path(__file__).resolve().parent / "models"

FAULT_MODEL_PATH = MODEL_DIR / "fault_prediction_xgboost.joblib"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_isolation_forest.joblib"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"

ALERT_CONFIDENCE_THRESHOLD = 0.8
RECENT_FAULT_WINDOW_MINUTES = 10


def load_models():
    anomaly_model = joblib.load(ANOMALY_MODEL_PATH)
    fault_model = joblib.load(FAULT_MODEL_PATH)
    label_encoder = joblib.load(LABEL_ENCODER_PATH)

    return anomaly_model, fault_model, label_encoder


def ensure_predictions_table(engine):
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS predictions (
            id SERIAL PRIMARY KEY,
            substation VARCHAR(50) NOT NULL,
            predicted_fault VARCHAR(100) NOT NULL,
            probability DOUBLE PRECISION NOT NULL,
            anomaly BOOLEAN DEFAULT FALSE,
            anomaly_score DOUBLE PRECISION DEFAULT 0,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """

    with engine.begin() as connection:
        connection.execute(text(create_table_sql))


def insert_prediction(
    engine,
    substation: str,
    predicted_fault: str,
    probability: float,
    anomaly: bool,
    anomaly_score: float,
):
    insert_sql = """
        INSERT INTO predictions (
            substation,
            predicted_fault,
            probability,
            anomaly,
            anomaly_score,
            timestamp
        )
        VALUES (
            :substation,
            :predicted_fault,
            :probability,
            :anomaly,
            :anomaly_score,
            NOW()
        )
    """

    with engine.begin() as connection:
        connection.execute(
            text(insert_sql),
            {
                "substation": substation,
                "predicted_fault": predicted_fault,
                "probability": probability,
                "anomaly": anomaly,
                "anomaly_score": anomaly_score,
            },
        )


def create_ai_alert_if_needed(
    engine,
    substation: str,
    predicted_fault: str,
    probability: float,
    anomaly: bool,
    anomaly_score: float,
):
    high_confidence_fault = (
        predicted_fault != "normal"
        and probability >= ALERT_CONFIDENCE_THRESHOLD
    )

    if not high_confidence_fault and not anomaly:
        return

    fault_type = (
        "ai_anomaly_detected"
        if predicted_fault == "normal" and anomaly
        else f"ai_predicted_{predicted_fault}"
    )

    severity = "critical" if probability >= 0.9 or anomaly_score >= 0.8 else "high"

    recent_duplicate_sql = """
        SELECT 1
        FROM faults
        WHERE substation = :substation
          AND fault_type = :fault_type
          AND timestamp >= NOW() - (:recent_fault_window_minutes * INTERVAL '1 minute')
        LIMIT 1
    """

    insert_sql = """
        INSERT INTO faults (
            substation,
            fault_type,
            severity,
            timestamp
        )
        VALUES (
            :substation,
            :fault_type,
            :severity,
            NOW()
        )
    """

    with engine.begin() as connection:
        recent_duplicate = connection.execute(
            text(recent_duplicate_sql),
            {
                "substation": substation,
                "fault_type": fault_type,
                "recent_fault_window_minutes": RECENT_FAULT_WINDOW_MINUTES,
            },
        ).scalar()

        if recent_duplicate:
            return

        connection.execute(
            text(insert_sql),
            {
                "substation": substation,
                "fault_type": fault_type,
                "severity": severity,
            },
        )


def predict_latest():
    engine = get_engine()
    ensure_predictions_table(engine)

    anomaly_model, fault_model, label_encoder = load_models()

    telemetry_dataframe = load_latest_telemetry_per_substation()

    if telemetry_dataframe.empty:
        print("No telemetry data found for prediction.")
        return []

    feature_values = telemetry_dataframe[FEATURE_COLUMNS]

    fault_probabilities = fault_model.predict_proba(feature_values)
    fault_class_indexes = fault_probabilities.argmax(axis=1)

    anomaly_results = calculate_anomaly_score(anomaly_model, feature_values)

    prediction_results = []

    for row_index, row in telemetry_dataframe.reset_index(drop=True).iterrows():
        predicted_class_index = fault_class_indexes[row_index]
        predicted_fault = label_encoder.inverse_transform([predicted_class_index])[0]
        probability = round(float(fault_probabilities[row_index][predicted_class_index]), 4)

        anomaly_result = anomaly_results[row_index]
        anomaly = anomaly_result["anomaly"]
        anomaly_score = anomaly_result["score"]

        substation = row["substation"]

        insert_prediction(
            engine=engine,
            substation=substation,
            predicted_fault=predicted_fault,
            probability=probability,
            anomaly=anomaly,
            anomaly_score=anomaly_score,
        )

        create_ai_alert_if_needed(
            engine=engine,
            substation=substation,
            predicted_fault=predicted_fault,
            probability=probability,
            anomaly=anomaly,
            anomaly_score=anomaly_score,
        )

        prediction_results.append(
            {
                "substation": substation,
                "predicted_fault": predicted_fault,
                "probability": probability,
                "anomaly": anomaly,
                "anomaly_score": anomaly_score,
            }
        )

    return prediction_results


def main():
    results = predict_latest()

    print("V.E.N.U.S prediction results:")

    for result in results:
        print(result)


if __name__ == "__main__":
    main()