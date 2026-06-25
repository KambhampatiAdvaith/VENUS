from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.models import Fault
from backend.api.schemas import FaultResponse


router = APIRouter(
    prefix="/faults",
    tags=["Faults"],
)


@router.get("", response_model=list[FaultResponse])
def get_faults(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return (
        db.query(Fault)
        .order_by(desc(Fault.timestamp))
        .limit(limit)
        .all()
    )