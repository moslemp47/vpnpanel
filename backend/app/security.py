from datetime import datetime, timedelta, timezone
import jwt
from passlib.context import CryptContext
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_token(subject: dict, expires_minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"exp": now + timedelta(minutes=expires_minutes), "iat": now, "nbf": now, **subject}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


import uuid

def create_access_token(user_id: int) -> str:
    return create_token({"sub": str(user_id), "scope": "access"}, settings.ACCESS_TOKEN_EXPIRE_MINUTES)

def create_refresh_token(user_id: int, jti: str | None = None, minutes: int | None = None) -> str:
    jti = jti or uuid.uuid4().hex
    minutes = minutes or (settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60)
    return create_token({"sub": str(user_id), "scope": "refresh", "jti": jti}, minutes)
