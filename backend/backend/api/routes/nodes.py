from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.fault_window import get_active_fault_counts_by_substation
from backend.api.schemas import NodeStatusResponse


router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
)


def get_node_status(
    *,
    temperature: float,
    voltage: float,
    frequency: float,
    load: float,
    fault_count: int,
) -> tuple[str, str | None]:
    """Return (status, reason)

    Status logic (strict):
    - CRITICAL: any one of
        - load >= 80%
        - temperature >= 70°C
        - voltage < 210V or voltage > 240V
        - frequency < 49.3 Hz or frequency > 50.7 Hz
    - WARNING: any one of
        - load between 75% and 79% (inclusive lower bound, <80)
        - temperature between 65°C and 69°C (>=65 and <70)
        - voltage between 210V and 218V (>=210 and <218)
        - frequency between 49.3–49.5 (>=49.3 and <49.5) or 50.5–50.7 (>50.5 and <=50.7)
    - HEALTHY: all values within the healthy band
        - load < 75%
        - voltage between 218V and 237V (inclusive)
        - temperature < 65°C
        - frequency between 49.5 Hz and 50.5 Hz (inclusive)

    Active fault_count events are treated as CRITICAL.
    """
    # If there's an active fault record, treat as critical
    if fault_count and fault_count > 0:
        return "critical", "Active fault event"

    # Normalize None values defensively (if telemetry has missing fields)
    try:
        _load = float(load)
        _voltage = float(voltage)
        _temperature = float(temperature)
        _frequency = float(frequency)
    except Exception:
        # If we cannot interpret values, return healthy fallback to avoid false alarms
        return "healthy", None

    # Critical conditions
    if (
        _load >= 80.0
        or _temperature >= 70.0
        or _voltage < 210.0
        or _voltage > 240.0
        or _frequency < 49.3
        or _frequency > 50.7
    ):
        return "critical", "Threshold breached"

    # Warning conditions
    if (
        (75.0 <= _load < 80.0)
        or (65.0 <= _temperature < 70.0)
        or (210.0 <= _voltage < 218.0)
        or (49.3 <= _frequency < 49.5)
        or (50.5 < _frequency <= 50.7)
    ):
        return "warning", "Near-threshold"

    # All values within healthy range
    return "healthy", None


@router.get("", response_model=list[NodeStatusResponse])
def get_nodes(db: Session = Depends(get_db)):
    active_fault_counts = get_active_fault_counts_by_substation(db)

    query = """
        WITH latest_by_ingest AS (
            SELECT DISTINCT ON (substation)
                substation,
                voltage,
                temperature,
                "load" AS load,
                frequency,
                "timestamp",
                database_written_at
            FROM telemetry
            WHERE database_written_at IS NOT NULL
            ORDER BY
                substation,
                database_written_at DESC,
                id DESC
        ),
        latest_by_payload AS (
            SELECT DISTINCT ON (substation)
                substation,
                voltage,
                temperature,
                "load" AS load,
                frequency,
                "timestamp",
                database_written_at
            FROM telemetry
            WHERE database_written_at IS NULL
            ORDER BY
                substation,
                "timestamp" DESC,
                id DESC
        ),
        latest_telemetry AS (
            SELECT *
            FROM latest_by_ingest
            UNION ALL
            SELECT latest_by_payload.*
            FROM latest_by_payload
            WHERE NOT EXISTS (
                SELECT 1
                FROM latest_by_ingest
                WHERE latest_by_ingest.substation = latest_by_payload.substation
            )
        )
        SELECT
            latest_telemetry.substation,
            latest_telemetry.voltage,
            latest_telemetry.temperature,
            latest_telemetry.load,
            latest_telemetry.frequency,
            latest_telemetry.timestamp,
            latest_telemetry.database_written_at
        FROM latest_telemetry
        ORDER BY latest_telemetry.substation
    """

    latest_telemetry = db.execute(text(query)).mappings().all()

    nodes = []

    for telemetry in latest_telemetry:
        status, reason = get_node_status(
            temperature=telemetry["temperature"],
            voltage=telemetry["voltage"],
            frequency=telemetry["frequency"],
            load=telemetry["load"],
            fault_count=active_fault_counts.get(telemetry["substation"], 0),
        )

        nodes.append(
            {
                "node": telemetry["substation"],
                "status": status,
                "reason": reason,
                "load": telemetry["load"],
                "voltage": telemetry["voltage"],
                "temperature": telemetry["temperature"],
                "frequency": telemetry["frequency"],
                "last_updated": telemetry["database_written_at"] or telemetry["timestamp"],
            }
        )

    return nodes
