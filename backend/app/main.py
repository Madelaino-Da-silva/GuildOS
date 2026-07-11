"""
GuildOS FastAPI application entrypoint.

Run with:
    uvicorn app.main:app --host 0.0.0.0 --port 8000

Or via Docker Compose (see docker-compose.yml at the project root).
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import init_models
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("guildos.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (%s environment)", settings.APP_NAME, settings.ENVIRONMENT)
    # NOTE: In production, prefer `alembic upgrade head` over init_models().
    # init_models() is a convenience for first-run local development only.
    if settings.ENVIRONMENT == "development":
        await init_models()
        logger.info("Database tables ensured (development mode)")
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered management system for the Outsiders Minecraft guild.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}
