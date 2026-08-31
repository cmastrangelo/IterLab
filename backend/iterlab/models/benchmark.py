from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Benchmark(UUIDPrimaryKey, Timestamps, Base):
    """A named, repeatable evaluation that produces a comparable score."""

    __tablename__ = "benchmarks"

    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # which BenchmarkAdapter runs this benchmark (registry key), e.g.
    # "sql_leaderboard", "locm_round_robin".
    adapter: Mapped[str] = mapped_column(String(80), nullable=False)
    # adapter-specific configuration (connection refs, queries, params).
    # backend-agnostic; never contains secrets directly, only *_env references.
    spec: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)

    # the headline metric this benchmark resolves to (e.g. "win_pct", "rank").
    primary_metric: Mapped[str | None] = mapped_column(String(80))
    # higher score is better? used when ranking candidates
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # true when created/maintained by the instance lab loader (read-only via API)
    managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class BenchmarkResult(UUIDPrimaryKey, Timestamps, Base):
    """One candidate's result on one benchmark."""

    __tablename__ = "benchmark_results"

    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("benchmarks.id", ondelete="CASCADE"), index=True, nullable=False
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"), index=True
    )

    score: Mapped[float | None] = mapped_column()
    passed: Mapped[bool | None] = mapped_column(Boolean)
    details: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
