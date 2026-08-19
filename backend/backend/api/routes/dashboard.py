from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.fault_window import (
    count_active_faults,
    get_system_health_for_active_faults,
)
from backend.api.models import Telemetry
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

    active_faults = count_active_faults(db)

    avg_load_result = db.query(func.avg(Telemetry.load)).scalar()
    avg_load = round(float(avg_load_result), 2) if avg_load_result else 0.0

    # Prioritize active faults for system health; otherwise derive from average load
    if active_faults > 0:
        system_health = get_system_health_for_active_faults(active_faults)
    else:
        # Derive health from average load when there are no active faults
        if avg_load >= 80:
            system_health = "critical"
        elif avg_load >= 60:
            system_health = "warning"
        else:
            system_health = "healthy"

    return {
        "total_nodes": total_nodes,
        "active_faults": active_faults,
        "avg_load": avg_load,
        "system_health": system_health,
    }
