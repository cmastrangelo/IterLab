"""Schema + table bootstrap.

Runs at application startup when ``ITERLAB_DB_AUTO_CREATE`` is true. It:

1. waits for the database to accept connections (compose start ordering);
2. creates IterLab's schema if it does not exist (PostgreSQL);
3. creates any missing tables from the SQLAlchemy metadata.

This is intentionally idempotent and safe against an *existing* external
database — it only ever creates its own schema and its own tables, and never
drops or alters anything. Production deployments should disable auto-create and
use Alembic instead.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from iterlab import models  # noqa: F401  (register models on Base.metadata)
from iterlab.config import get_settings
from iterlab.db.base import Base
from iterlab.db.session import get_engine

logger = logging.getLogger("iterlab.bootstrap")


async def _wait_for_db() -> None:
    settings = get_settings()
    engine = get_engine()
    last_err: Exception | None = None
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return
        except Exception as err:  # noqa: BLE001 - want to retry on anything
            last_err = err
            logger.warning(
                "database not ready (attempt %d/%d): %s",
                attempt,
                settings.db_connect_retries,
                err,
            )
            await asyncio.sleep(settings.db_connect_retry_delay)
    raise RuntimeError(f"database unreachable after retries: {last_err}")


async def _create_schema() -> None:
    settings = get_settings()
    if not settings.database_url.startswith("postgresql"):
        return
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.db_schema}"'))
    logger.info("ensured schema %r exists", settings.db_schema)


async def _create_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("ensured %d tables exist", len(Base.metadata.tables))


async def bootstrap_database() -> None:
    settings = get_settings()
    await _wait_for_db()
    if not settings.db_auto_create:
        logger.info("ITERLAB_DB_AUTO_CREATE is false — skipping schema/table bootstrap")
        return
    await _create_schema()
    await _create_tables()
