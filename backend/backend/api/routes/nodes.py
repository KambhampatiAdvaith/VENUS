from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.fault_window import (
    ensure_utc_datetime,
    get_active_fault_summary_by_substation,
)
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
    has_critical_fault: bool,
) -> tuple[str, str | None]:
    """Return (status, reason)"""
    if has_critical_fault:
        return "fault", "Active fault event"

    if fault_count > 0:
        return "warning", "Active non-critical fault event"

    if (
        temperature > 85
        or voltage < 210
        or voltage > 250
        or frequency < 49.5
        or frequency > 50.5
        or load > 80
    ):
        return "warning", "Threshold exceeded"

    return "healthy", None


@router.get("", response_model=list[NodeStatusResponse])
def get_nodes(db: Session = Depends(get_db)):
    active_fault_summary = get_active_fault_summary_by_substation(db)

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
        fault_summary = active_fault_summary.get(
            telemetry["substation"],
            {"count": 0, "has_critical": False, "latest_fault_at": None},
        )

        status, reason = get_node_status(
            temperature=telemetry["temperature"],
            voltage=telemetry["voltage"],
            frequency=telemetry["frequency"],
            load=telemetry["load"],
            fault_count=int(fault_summary["count"]),
            has_critical_fault=bool(fault_summary["has_critical"]),
        )

        last_updated = telemetry["database_written_at"] or telemetry["timestamp"]

        nodes.append(
            {
                "node": telemetry["substation"],
                "status": status,
                "reason": reason,
                "load": telemetry["load"],
                "voltage": telemetry["voltage"],
                "temperature": telemetry["temperature"],
                "frequency": telemetry["frequency"],
                "last_updated": ensure_utc_datetime(last_updated),
            }
        )

    return nodes
