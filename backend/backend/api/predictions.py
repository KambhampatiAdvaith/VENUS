import asyncio
from datetime import datetime

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.ai.predict import predict_latest
from backend.api.database import get_engine
from backend.api.ws_manager import manager


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
async def run_predictions():
    fault_events = []
    results = await asyncio.to_thread(predict_latest, fault_events.append)

    for fault_event in fault_events:
        await manager.broadcast("fault", fault_event)

    await manager.broadcast(
        "prediction",
        {
            "count": len(results),
            "message": "V.E.N.U.S AI prediction cycle completed",
        },
    )

    return {
        "message": "V.E.N.U.S AI prediction cycle completed",
        "count": len(results),
        "predictions": results,
    }


@router.get("/predictions/metrics")
def get_prediction_metrics():
    engine = get_engine()

    # Records Analysed: total latest-per-substation records
    # Predicted Faults: latest-per-substation where predicted_fault != 'normal'
    # High Risk: predicted_fault != 'normal' AND probability >= 0.6 (high or critical)
    # Avg Fault Confidence: average probability across predicted_fault != 'normal' only
    query = """
        SELECT
            COUNT(*) AS records_analysed,
            COUNT(*) FILTER (
                WHERE predicted_fault != 'normal'
            ) AS predicted_faults,
            COALESCE(
                AVG(probability) FILTER (WHERE predicted_fault != 'normal'),
                0
            ) AS average_fault_confidence,
            COUNT(*) FILTER (
                WHERE predicted_fault != 'normal'
                AND probability >= 0.6
            ) AS high_risk_count,
            COUNT(*) FILTER (
                WHERE predicted_fault != 'normal'
                AND probability >= 0.4
                AND probability < 0.6
            ) AS medium_risk_count
        FROM (
            SELECT DISTINCT ON (substation)
                substation,
                predicted_fault,
                probability,
                timestamp
            FROM predictions
            ORDER BY substation, timestamp DESC
        ) latest_predictions
    """

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    records_analysed = int(row["records_analysed"] or 0)
    predicted_faults = int(row["predicted_faults"] or 0)
    average_fault_confidence = float(row["average_fault_confidence"] or 0)
    high_risk_count = int(row["high_risk_count"] or 0)
    medium_risk_count = int(row["medium_risk_count"] or 0)

    if high_risk_count > 0:
        system_risk_level = "high"
    elif medium_risk_count > 0:
        system_risk_level = "medium"
    else:
        system_risk_level = "low"

    return {
        "records_analysed": records_analysed,
        "predicted_faults": predicted_faults,
        # risk_score kept for backward compatibility but now represents
        # "Avg Fault Confidence" (percentage 0..100) computed only over flagged faults
        "risk_score": round(average_fault_confidence * 100, 2),
        "system_risk_level": system_risk_level,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
    }
