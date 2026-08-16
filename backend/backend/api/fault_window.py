import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.models import Fault


ACTIVE_FAULT_WINDOW_ENV_VAR = "ACTIVE_FAULT_WINDOW_MINUTES"
DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES = 10


def get_active_fault_window_minutes() -> int:
    raw_value = os.getenv(ACTIVE_FAULT_WINDOW_ENV_VAR, "").strip()

    try:
        minutes = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES

    if minutes <= 0:
        return DEFAULT_ACTIVE_FAULT_WINDOW_MINUTES

    return minutes


def get_active_fault_cutoff(now: datetime | None = None) -> datetime:
    current_time = now or datetime.now(timezone.utc)
    return current_time - timedelta(minutes=get_active_fault_window_minutes())


def get_active_fault_counts_by_substation(
    db: Session,
    now: datetime | None = None,
) -> dict[str, int]:
    cutoff = get_active_fault_cutoff(now)
    rows = (
        db.query(Fault.substation, func.count(Fault.id))
        .filter(Fault.timestamp >= cutoff)
        .group_by(Fault.substation)
        .all()
    )
    return {substation: fault_count for substation, fault_count in rows}


def count_active_faults(db: Session, now: datetime | None = None) -> int:
    cutoff = get_active_fault_cutoff(now)
    return db.query(Fault).filter(Fault.timestamp >= cutoff).count()


def get_system_health_for_active_faults(active_faults: int) -> str:
    if active_faults == 0:
        return "healthy"

    if active_faults <= 5:
        return "warning"

    return "critical"
