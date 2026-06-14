"""Database engines and session factories.

Two engines, by design (see docs/privacy.md):
  * ``engine`` — request-path, connects as the RLS-subject role. Every request
    session sets ``app.current_user_id`` so Postgres RLS scopes all queries.
  * ``synthesis_engine`` — isolated reader for AI synthesis only. May bypass RLS
    to read attendees' preferences server-side; never used by request handlers.
"""

from collections.abc import AsyncIterator

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# NullPool: one connection per request. Avoids asyncpg connections binding to a
# stale event loop (matters for tests) and keeps the SET LOCAL identity strictly
# per-request. Fine at hackathon scale; revisit pooling for production load.
engine: AsyncEngine = create_async_engine(settings.database_url, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Synthesis reader is optional until the AI step is wired (Step 6).
synthesis_engine: AsyncEngine | None = (
    create_async_engine(settings.database_url_synthesis, pool_pre_ping=True)
    if settings.database_url_synthesis
    else None
)
SynthesisSessionLocal: async_sessionmaker[AsyncSession] | None = (
    async_sessionmaker(synthesis_engine, expire_on_commit=False, class_=AsyncSession)
    if synthesis_engine
    else None
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped session.

    NOTE: this yields a session WITHOUT an RLS identity set. The auth-aware
    dependency added in Step 3 sets ``app.current_user_id`` per request.
    """
    async with SessionLocal() as session:
        yield session
