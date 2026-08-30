"""Declarative base and shared metadata.

The schema is *not* baked into the metadata so the models stay portable (the
test suite runs on SQLite). On PostgreSQL every connection sets ``search_path``
to ``ITERLAB_DB_SCHEMA`` (see ``db.session``), so tables are created and queried
inside IterLab's own schema without the models needing to know its name.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names — required for clean Alembic migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
