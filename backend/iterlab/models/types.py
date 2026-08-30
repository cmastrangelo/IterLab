"""Portable column types."""

from __future__ import annotations

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

# JSONB on PostgreSQL, plain JSON on SQLite (test suite).
JSONMap = JSON().with_variant(JSONB(), "postgresql")
