"""CoRoute FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.routers import auth, groups, plans, preferences

settings = get_settings()
log = get_logger("coroute")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    log.info("CoRoute API starting (env=%s)", settings.app_env)
    yield
    log.info("CoRoute API shutting down")


app = FastAPI(title="CoRoute API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(groups.router)
app.include_router(preferences.router)
app.include_router(plans.group_router)
app.include_router(plans.plan_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness check — does not touch the database."""
    return {"status": "ok", "service": "coroute", "env": settings.app_env}
