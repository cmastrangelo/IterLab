"""Async engine / session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from iterlab.config import Settings, get_settings


def _engine_kwargs(settings: Settings) -> dict:
    kwargs: dict = {"echo": settings.db_echo, "pool_pre_ping": True}
    if settings.database_url.startswith("postgresql"):
        # asyncpg: pin every connection to IterLab's schema. "public" stays on
        # the path so shared extensions (uuid-ossp, pgcrypto, ...) resolve.
        kwargs["connect_args"] = {
            "server_settings": {"search_path": f"{settings.db_schema},public"},
        }
    return kwargs


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(settings.database_url, **_engine_kwargs(settings))


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yields a session, commits on success, rolls back on error."""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    engine = get_engine()
    await engine.dispose()
