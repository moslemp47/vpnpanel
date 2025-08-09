from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..schemas import ProvisionRequest
from ..clients.marzban import MarzbanClient
from ..clients.sanaei import SanaeiClient
from datetime import datetime, timedelta
import secrets

from . import auth as auth_router
router = APIRouter(prefix="/admin", tags=["admin"])

def admin_only(db=Depends(get_db), user_id: int = Depends(auth_router.get_current_user_id)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_admin:
        raise HTTPException(403, "Admins only")
    return user

@router.post("/provision")
def provision(req: ProvisionRequest, db: Session = Depends(get_db), _admin = Depends(admin_only)):
    sub = db.query(models.Subscription).filter(models.Subscription.id == req.subscription_id).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")
    plan = db.query(models.Plan).filter(models.Plan.id == sub.plan_id).first()
    username = f"user{sub.user_id}_{sub.id}"
    password = secrets.token_urlsafe(8)

    if req.provider == "marzban":
        client = MarzbanClient()
        res = client.create_user(username, password, plan.quota_gb, plan.duration_days)
    else:
        client = SanaeiClient()
        res = client.create_user(username, password, plan.quota_gb, plan.duration_days)

    if "error" in res:
        raise HTTPException(502, f"Provision failed: {res['error']}")

    sub.provider = req.provider
    sub.external_username = username
    sub.external_id = str(res.get("id") or res.get("uuid") or "")
    sub.started_at = datetime.utcnow()
    sub.expires_at = datetime.utcnow() + timedelta(days=plan.duration_days)
    db.commit(); db.refresh(sub)
    return {"message": "Provisioned", "subscription_id": sub.id, "external": res}
