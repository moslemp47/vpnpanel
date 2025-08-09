from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "VPN Panel Pro"
    APP_DEBUG: bool = True
    APP_SECRET: str = "change-this-secret"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    DATABASE_URL: str = "sqlite:///./vpnpanel.db"
    JWT_SECRET: str = "please-change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RATE_LIMIT_PER_MINUTE: int = 120

    MARZBAN_API_URL: Optional[str] = None
    MARZBAN_TOKEN: Optional[str] = None
    SANAEI_API_URL: Optional[str] = None
    SANAEI_TOKEN: Optional[str] = None

    PAYMENT_PROVIDER: str = "mock"
    ZARINPAL_MERCHANT_ID: Optional[str] = None
    CALLBACK_BASE_URL: str = "http://localhost:8000"

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
if isinstance(settings.CORS_ORIGINS, str):
    settings.CORS_ORIGINS = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
