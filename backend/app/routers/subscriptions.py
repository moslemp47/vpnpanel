from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from . import auth as auth_router
from ..clients.marzban import MarzbanClient
from ..clients.sanaei import SanaeiClient

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

@router.get("")
def list_subscriptions(db: Session = Depends(get_db), user_id: int = Depends(auth_router.get_current_user_id)):
    subs = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()
    return [{
        "id": s.id,
        "plan_id": s.plan_id,
        "provider": s.provider,
        "external_username": s.external_username,
        "expires_at": s.expires_at.isoformat() if s.expires_at else None,
        "quota_gb": s.quota_gb,
        "used_gb": s.used_gb,
    } for s in subs]

@router.get("/{sub_id}/usage")
def usage(sub_id: int, db: Session = Depends(get_db), user_id: int = Depends(auth_router.get_current_user_id)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == sub_id, models.Subscription.user_id == user_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    if sub.provider == "marzban":
        client = MarzbanClient(); res = client.get_usage(sub.external_username or "")
    else:
        client = SanaeiClient(); res = client.get_usage(sub.external_username or "")
    return res
