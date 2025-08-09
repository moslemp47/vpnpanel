from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .middlewares.security_headers import SecurityHeadersMiddleware
from .middlewares.rate_limit import RateLimitMiddleware
from .config import settings
from .database import engine, Base
from .routers import auth, catalog, orders, admin, subscriptions

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, limit=settings.RATE_LIMIT_PER_MINUTE, window_seconds=60)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(admin.router)
app.include_router(subscriptions.router)

@app.get("/health")
def health():
    return {"status": "ok"}
