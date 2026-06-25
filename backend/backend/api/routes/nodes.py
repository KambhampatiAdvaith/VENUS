from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.models import Fault, Telemetry
from backend.api.schemas import NodeStatusResponse


router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
)


def get_node_status(
    telemetry: Telemetry,
    fault_count: int,
) -> str:
    if fault_count > 0:
        return "fault"

    if (
        telemetry.temperature > 85
        or telemetry.voltage < 210
        or telemetry.voltage > 250
        or telemetry.frequency < 49.5
        or telemetry.frequency > 50.5
        or telemetry.load > 80
    ):
        return "warning"

    return "healthy"


@router.get("", response_model=list[NodeStatusResponse])
def get_nodes(db: Session = Depends(get_db)):
    latest_subquery = (
        db.query(
            Telemetry.substation,
            func.max(Telemetry.timestamp).label("latest_timestamp"),
        )
        .group_by(Telemetry.substation)
        .subquery()
    )

    latest_telemetry = (
        db.query(Telemetry)
        .join(
            latest_subquery,
            (Telemetry.substation == latest_subquery.c.substation)
            & (Telemetry.timestamp == latest_subquery.c.latest_timestamp),
        )
        .order_by(Telemetry.substation)
        .all()
    )

    nodes = []

    for telemetry in latest_telemetry:
        fault_count = (
            db.query(Fault)
            .filter(Fault.substation == telemetry.substation)
            .count()
        )

        nodes.append(
            {
                "node": telemetry.substation,
                "status": get_node_status(telemetry, fault_count),
                "load": telemetry.load,
                "voltage": telemetry.voltage,
                "temperature": telemetry.temperature,
                "frequency": telemetry.frequency,
                "last_updated": telemetry.timestamp,
            }
        )

    return nodes