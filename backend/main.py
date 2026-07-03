import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import init_db, SessionLocal
from app.rate_limit import limiter
from app.routers import areas, data_sources
from app.routers import admin
from app.routers import billing
from app.routers import alerts
from app.routers import api_keys

app = FastAPI(title="LandSignal AI", version="0.5.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SlowAPIMiddleware)
_cors_origins = ["http://localhost:4173"]
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
if _frontend_url:
    _cors_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Allow any localhost port so Vite's port-increment fallback always works
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(areas.router)
app.include_router(data_sources.router)
app.include_router(admin.router)
app.include_router(billing.router)
app.include_router(alerts.router)
app.include_router(api_keys.router)


@app.on_event("startup")
async def startup():
    init_db()  # creates tables + runs upgrade_db() for new columns
    db = SessionLocal()
    try:
        from app.seed_plans import seed_plans
        seed_plans(db)
    finally:
        db.close()
    from app.scheduler import start_scheduler
    start_scheduler()


@app.on_event("shutdown")
async def shutdown():
    from app.scheduler import stop_scheduler
    stop_scheduler()


@app.get("/health")
@limiter.exempt
def health():
    return {"status": "ok", "service": "LandSignal AI", "version": "0.5.0"}
