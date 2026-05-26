from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.usage_service import usage_for_rfp, usage_summary

router = APIRouter(tags=["usage"])


@router.get("/usage/summary")
def get_usage_summary(db: Session = Depends(get_db)) -> dict:
    return usage_summary(db)


@router.get("/rfps/{rfp_id}/usage")
def get_rfp_usage(rfp_id: int, db: Session = Depends(get_db)) -> dict:
    return usage_for_rfp(db, rfp_id)
