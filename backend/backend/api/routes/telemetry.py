import os
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import create_engine, text

from backend.api.schemas import TelemetryRecord


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql://venus:venus@localhost:5432/venus_db",
    )


def get_engine():
    return create_engine(get_database_url())


@router.get("", response_model=list[TelemetryRecord])
def get_telemetry(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """
    Returns latest telemetry records, including Week 6 edge anomaly fields.
    """
    query = """
        SELECT
            id,
            substation,
            voltage,
            current,
            temperature,
            load,
            frequency,
            timestamp,
            edge_anomaly,
            edge_anomaly_score,
            edge_model,
            edge_processed_at
        FROM telemetry
        ORDER BY timestamp DESC, id DESC
        LIMIT :limit
    """

    engine = get_engine()

    with engine.begin() as connection:
        rows = connection.execute(
            text(query),
            {"limit": limit},
        ).mappings().all()

    return [dict(row) for row in rows]


@router.get("/latest", response_model=TelemetryRecord | None)
def get_latest_telemetry() -> dict[str, Any] | None:
    """
    Returns the single latest telemetry record.
    """
    query = """
        SELECT
            id,
            substation,
            voltage,
            current,
            temperature,
            load,
            frequency,
            timestamp,
            edge_anomaly,
            edge_anomaly_score,
            edge_model,
            edge_processed_at
        FROM telemetry
        ORDER BY timestamp DESC, id DESC
        LIMIT 1
    """

    engine = get_engine()

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    if row is None:
        return None

    return dict(row)