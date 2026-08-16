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
) -> str:
    if fault_count > 0:
        return "fault"

    if (
        temperature > 85
        or voltage < 210
        or voltage > 250
        or frequency < 49.5
        or frequency > 50.5
        or load > 80
    ):
        return "warning"

    return "healthy"


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
        nodes.append(
            {
                "node": telemetry["substation"],
                "status": get_node_status(
                    temperature=telemetry["temperature"],
                    voltage=telemetry["voltage"],
                    frequency=telemetry["frequency"],
                    load=telemetry["load"],
                    fault_count=active_fault_counts.get(
                        telemetry["substation"],
                        0,
                    ),
                ),
                "load": telemetry["load"],
                "voltage": telemetry["voltage"],
                "temperature": telemetry["temperature"],
                "frequency": telemetry["frequency"],
                "last_updated": telemetry["database_written_at"]
                or telemetry["timestamp"],
            }
        )

    return nodes