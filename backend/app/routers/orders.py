from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..schemas import CreateOrderRequest, OrderOut
from ..config import settings
from . import auth as auth_router

router = APIRouter(prefix="/orders", tags=["orders"])

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

@router.post("", response_model=OrderOut)
def create_order(data: CreateOrderRequest, user_id: int = Depends(auth_router.get_current_user_id), db: Session = Depends(get_db)):
    plan = db.query(models.Plan).filter(models.Plan.id == data.plan_id).first()
    if not plan:
        raise HTTPException(404, "Plan not found")
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(401, "Unauthorized")
    order = models.Order(user_id=user.id, plan_id=plan.id, amount=plan.price, status="pending")
    db.add(order); db.commit(); db.refresh(order)
    if settings.PAYMENT_PROVIDER == "mock":
        order.status = "paid"
        db.commit(); db.refresh(order)
        sub = models.Subscription(user_id=user.id, plan_id=plan.id, quota_gb=plan.quota_gb)
        db.add(sub); db.commit(); db.refresh(sub)
        order.subscription_id = sub.id  # type: ignore
    return order
