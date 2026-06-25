from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.models import Fault, Telemetry
from backend.api.schemas import DashboardMetricsResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


@router.get("/metrics", response_model=DashboardMetricsResponse)
def get_dashboard_metrics(db: Session = Depends(get_db)):
    total_nodes = (
        db.query(Telemetry.substation)
        .distinct()
        .count()
    )

    active_faults = db.query(Fault).count()

    avg_load_result = db.query(func.avg(Telemetry.load)).scalar()
    avg_load = round(float(avg_load_result), 2) if avg_load_result else 0.0

    if active_faults == 0:
        system_health = "healthy"
    elif active_faults <= 5:
        system_health = "warning"
    else:
        system_health = "critical"

    return {
        "total_nodes": total_nodes,
        "active_faults": active_faults,
        "avg_load": avg_load,
        "system_health": system_health,
    }