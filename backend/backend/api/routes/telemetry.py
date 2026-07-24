from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import text

from backend.api.database import get_engine
from backend.api.schemas import TelemetryRecord


router = APIRouter(
    prefix="/telemetry",
    tags=["Telemetry"],
)

_TELEMETRY_COLUMNS = """
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
    edge_processed_at,
    generated_at,
    kafka_received_at,
    database_written_at
"""


@router.get("", response_model=list[TelemetryRecord])
def get_telemetry(
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """
    Returns latest telemetry records, including Week 6 edge anomaly fields
    and Week 7 latency timestamp fields.
    """
    query = f"""
        SELECT {_TELEMETRY_COLUMNS}
        FROM telemetry
        ORDER BY COALESCE(database_written_at, timestamp) DESC, id DESC
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
    query = f"""
        SELECT {_TELEMETRY_COLUMNS}
        FROM telemetry
        ORDER BY COALESCE(database_written_at, timestamp) DESC, id DESC
        LIMIT 1
    """

    engine = get_engine()

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    if row is None:
        return None

    return dict(row)


@router.get("/latency")
def get_latency_metrics() -> dict[str, Any]:
    """
    Returns end-to-end latency metrics computed from available timestamp fields.

    Uses recent rows only. Prefers database_written_at - kafka_received_at
    for pipeline latency and only falls back to generated_at when the delta
    is sane, excluding negative and extreme outliers.
    """
    query = """
        WITH candidate_latencies AS (
            SELECT
                CASE
                    WHEN kafka_received_at IS NOT NULL
                         AND database_written_at >= kafka_received_at
                         AND database_written_at - kafka_received_at <= INTERVAL '5 minutes'
                    THEN EXTRACT(EPOCH FROM (
                        database_written_at - kafka_received_at
                    )) * 1000
                    WHEN generated_at IS NOT NULL
                         AND database_written_at >= generated_at
                         AND database_written_at - generated_at <= INTERVAL '5 minutes'
                    THEN EXTRACT(EPOCH FROM (
                        database_written_at - generated_at
                    )) * 1000
                    ELSE NULL
                END AS latency_ms
            FROM telemetry
            WHERE database_written_at IS NOT NULL
              AND database_written_at >= NOW() - INTERVAL '15 minutes'
            ORDER BY database_written_at DESC
            LIMIT 500
        ),
        sane_latencies AS (
            SELECT latency_ms
            FROM candidate_latencies
            WHERE latency_ms IS NOT NULL
              AND latency_ms BETWEEN 0 AND 300000
        )
        SELECT
            COUNT(*) AS sample_count,
            AVG(latency_ms) AS avg_latency_ms,
            MIN(latency_ms) AS min_latency_ms,
            MAX(latency_ms) AS max_latency_ms,
            PERCENTILE_CONT(0.5) WITHIN GROUP (
                ORDER BY latency_ms
            ) AS median_latency_ms
        FROM sane_latencies
    """

    engine = get_engine()

    with engine.begin() as connection:
        row = connection.execute(text(query)).mappings().first()

    if row is None or row["sample_count"] == 0:
        return {
            "sample_count": 0,
            "avg_latency_ms": None,
            "min_latency_ms": None,
            "max_latency_ms": None,
            "median_latency_ms": None,
        }

    def _round(val: Any) -> float | None:
        if val is None:
            return None
        return round(float(val), 2)

    return {
        "sample_count": int(row["sample_count"]),
        "avg_latency_ms": _round(row["avg_latency_ms"]),
        "min_latency_ms": _round(row["min_latency_ms"]),
        "max_latency_ms": _round(row["max_latency_ms"]),
        "median_latency_ms": _round(row["median_latency_ms"]),
    }
