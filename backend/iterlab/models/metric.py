from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Metric(UUIDPrimaryKey, Base):
    """A single time-series measurement.

    Deliberately generic: ``name`` + ``value`` + a set of nullable foreign keys
    identifying the subject (candidate / run / experiment / lab). Powers the
    performance / cost / model-effectiveness graphs.
    """

    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_subject", "lab_id", "name", "recorded_at"),
    )

    # e.g. score, cost_usd, tokens, latency_ms
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str | None] = mapped_column(String(40))

    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True
    )
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), index=True
    )

    labels: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
