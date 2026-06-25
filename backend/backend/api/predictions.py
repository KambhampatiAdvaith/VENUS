from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.ai.predict import predict_latest
from backend.api.database import get_engine


router = APIRouter()


def serialize_row(row):
    item = dict(row)

    if isinstance(item.get("timestamp"), datetime):
        item["timestamp"] = item["timestamp"].isoformat()

    return item


@router.get("/predictions")
def get_predictions(limit: int = Query(default=50, ge=1, le=500)):
    engine = get_engine()

    query = """
        SELECT
            id,
            substation,
            predicted_fault,
            probability,
            anomaly,
            anomaly_score,
            timestamp
        FROM predictions
        ORDER BY timestamp DESC
        LIMIT :limit
    """

    with engine.begin() as connection:
        rows = connection.execute(text(query), {"limit": limit}).mappings().all()

    return [serialize_row(row) for row in rows]


@router.post("/predictions/run")
def run_predictions():
    results = predict_latest()

    return {
        "message": "V.E.N.U.S AI prediction cycle completed",
        "count": len(results),
        "predictions": results,
    }


@router.get("/predictions/metrics")
def get_prediction_metrics():
    engine = get_engine()

    query = """
        SELECT
            COUNT(*) FILTER (
                WHERE predicted_fault != 'normal'
                OR anomaly = TRUE
            ) AS predicted_faults,
            COALESCE(AVG(probability), 0) AS average_confidence,
            COUNT(*) FILTER (
                WHERE (
                    predicted_fault != 'normal'
                    AND probability >= 0.8
                )
                OR anomaly = TRUE
            ) AS high_risk_count,
            COUNT(*) FILTER (
                WHERE predicted_fault != 'normal'
                AND probability >= 0.5
            ) AS medium_risk_count
        FROM (
            SELECT DISTINCT ON (substation)
                substation,
                predicted_fault,
                probability,
                anomaly,
                timestamp
            FROM predictions
            ORDER BY substation, timestamp DESC
        ) latest_predictions
    """

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    predicted_faults = int(row["predicted_faults"] or 0)
    average_confidence = float(row["average_confidence"] or 0)
    high_risk_count = int(row["high_risk_count"] or 0)
    medium_risk_count = int(row["medium_risk_count"] or 0)

    if high_risk_count > 0:
        system_risk_level = "high"
    elif medium_risk_count > 0:
        system_risk_level = "medium"
    else:
        system_risk_level = "low"

    return {
        "predicted_faults": predicted_faults,
        "risk_score": round(average_confidence * 100, 2),
        "system_risk_level": system_risk_level,
    }