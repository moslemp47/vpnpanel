from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models
from ..models import RefreshToken
from ..schemas import SignupRequest, LoginRequest, TokenPair
from ..security import hash_password, verify_password, create_token, create_access_token, create_refresh_token
from ..config import settings
from datetime import datetime, timedelta

import time

# Simple in-memory login attempts throttle
from collections import defaultdict, deque
_login_attempts = defaultdict(deque)
def _throttle_ok(ip: str, max_attempts: int = 5, window_sec: int = 300) -> bool:
    now = time.time()
    dq = _login_attempts[ip]
    while dq and now - dq[0] > window_sec:
        dq.popleft()
    if len(dq) >= max_attempts:
        return False
    dq.append(now)
    return True

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/signup", response_model=TokenPair)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email == data.email).first()
    if exists:
        raise HTTPException(400, "Email already registered")
    user = models.User(email=data.email, password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    access = create_token({"sub": str(user.id), "scope": "access"}, settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh = create_token({"sub": str(user.id), "scope": "refresh"}, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
    return TokenPair(access_token=access, refresh_token=refresh)

@router.post("/login", response_model=TokenPair)
def login(data: LoginRequest, db: Session = Depends(get_db), request = None):
    ip = request.client.host if request and request.client else 'unknown'
    if not _throttle_ok(ip):
        raise HTTPException(429, "Too many attempts, try later")
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")
    access = create_token({"sub": str(user.id), "scope": "access"}, settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh = create_token({"sub": str(user.id), "scope": "refresh"}, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
    return TokenPair(access_token=access, refresh_token=refresh)


from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from ..security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user_id(token: str = Depends(oauth2_scheme)) -> int:
    try:
        payload = decode_token(token)
        if payload.get("scope") not in ("access", "refresh"):
            raise Exception("Invalid scope")
        return int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


@router.get("/me")
def me(user_id: int = Depends(get_current_user_id)):
    return {"user_id": user_id}


from fastapi import Body
import uuid

@router.post("/refresh", response_model=TokenPair)
def refresh(refresh_token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
        if payload.get("scope") != "refresh":
            raise Exception("Invalid scope")
        jti = payload.get("jti")
        token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti, RefreshToken.revoked == False).first()
        if not token_row or token_row.expires_at < datetime.utcnow():
            raise HTTPException(401, "Refresh token invalid or expired")
        # rotate
        token_row.revoked = True
        new_jti = uuid.uuid4().hex
        db.add(RefreshToken(user_id=token_row.user_id, jti=new_jti, expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)))
        db.commit()
        access = create_access_token(token_row.user_id)
        new_refresh = create_refresh_token(token_row.user_id, jti=new_jti)
        return TokenPair(access_token=access, refresh_token=new_refresh)
    except Exception:
        raise HTTPException(401, "Invalid refresh token")

@router.post("/logout")
def logout(refresh_token: str = Body(..., embed=True), db: Session = Depends(get_db)):
    try:
        payload = decode_token(refresh_token)
        jti = payload.get("jti")
        token_row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if token_row:
            token_row.revoked = True
            db.commit()
        return {"message": "logged out"}
    except Exception:
        return {"message": "logged out"}
