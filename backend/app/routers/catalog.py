from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..schemas import PlanOut

router = APIRouter(prefix="/catalog", tags=["catalog"])

@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(models.Plan).all()
    if not plans:
        defaults = [
            models.Plan(name="Basic 30d / 50GB", price=5.0, duration_days=30, quota_gb=50),
            models.Plan(name="Pro 60d / 150GB", price=12.0, duration_days=60, quota_gb=150),
            models.Plan(name="Max 90d / 300GB", price=20.0, duration_days=90, quota_gb=300),
        ]
        db.add_all(defaults); db.commit()
        plans = db.query(models.Plan).all()
    return plans
