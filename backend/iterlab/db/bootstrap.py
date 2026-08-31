"""Schema + table bootstrap.

Runs at application startup when ``ITERLAB_DB_AUTO_CREATE`` is true. It:

1. waits for the database to accept connections (compose start ordering);
2. creates IterLab's schema if it does not exist (PostgreSQL);
3. creates any missing tables from the SQLAlchemy metadata;
4. adds any missing *columns* that are safe to add (nullable, or with a
   default) — so additive model changes during pre-Alembic development don't
   require a database reset.

It only ever creates its own schema, its own tables, and additive columns, and
never drops or alters existing data. Production deployments should disable
auto-create and use Alembic instead.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import Connection, inspect, text
from sqlalchemy.schema import CreateColumn

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


def _sync_columns_sync(conn: Connection) -> None:
    """Add model columns missing from existing tables, when safe to do so."""
    settings = get_settings()
    is_pg = settings.database_url.startswith("postgresql")
    schema = settings.db_schema if is_pg else None
    inspector = inspect(conn)
    existing_tables = set(inspector.get_table_names(schema=schema))
    dialect = conn.dialect

    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue  # _create_tables already handled brand-new tables
        db_cols = {c["name"]: c for c in inspector.get_columns(table.name, schema=schema)}
        have = set(db_cols)
        qualified = f'"{schema}".{table.name}' if schema else table.name

        # relax NOT NULL where the model now allows NULL (safe, additive-only)
        for column in table.columns:
            db_col = db_cols.get(column.name)
            if is_pg and db_col is not None and column.nullable and not db_col["nullable"]:
                conn.execute(
                    text(f'ALTER TABLE {qualified} ALTER COLUMN "{column.name}" DROP NOT NULL')
                )
                logger.info("relaxed NOT NULL on %s.%s", table.name, column.name)

        for column in table.columns:
            if column.name in have:
                continue
            safe = (
                column.nullable
                or column.default is not None
                or column.server_default is not None
            )
            if not safe:
                logger.warning(
                    "cannot auto-add NOT NULL column %s.%s (no default) — needs a migration",
                    table.name,
                    column.name,
                )
                continue
            ddl = CreateColumn(column).compile(dialect=dialect)
            conn.execute(text(f"ALTER TABLE {qualified} ADD COLUMN {ddl}"))
            logger.info("added missing column %s.%s", table.name, column.name)


async def _sync_columns() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(_sync_columns_sync)


async def bootstrap_database() -> None:
    settings = get_settings()
    await _wait_for_db()
    if not settings.db_auto_create:
        logger.info("ITERLAB_DB_AUTO_CREATE is false — skipping schema/table bootstrap")
        return
    await _create_schema()
    await _create_tables()
    await _sync_columns()
