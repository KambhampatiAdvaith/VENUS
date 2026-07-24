from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.database import get_db
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
    query = """
        WITH latest_telemetry AS (
            SELECT DISTINCT ON (substation)
                substation,
                voltage,
                temperature,
                "load" AS load,
                frequency,
                "timestamp",
                database_written_at
            FROM telemetry
            ORDER BY
                substation,
                COALESCE(database_written_at, "timestamp") DESC,
                id DESC
        ),
        fault_counts AS (
            SELECT substation, COUNT(*) AS fault_count
            FROM faults
            GROUP BY substation
        )
        SELECT
            latest_telemetry.substation,
            latest_telemetry.voltage,
            latest_telemetry.temperature,
            latest_telemetry.load,
            latest_telemetry.frequency,
            latest_telemetry.timestamp,
            latest_telemetry.database_written_at,
            COALESCE(fault_counts.fault_count, 0) AS fault_count
        FROM latest_telemetry
        LEFT JOIN fault_counts
          ON fault_counts.substation = latest_telemetry.substation
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
                    fault_count=telemetry["fault_count"],
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