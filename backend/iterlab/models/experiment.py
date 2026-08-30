from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.enums import RunStatus
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Experiment(UUIDPrimaryKey, Timestamps, Base):
    """A repeatable experiment definition within a lab."""

    __tablename__ = "experiments"

    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # hypothesis / objective and constraints (max iterations, budget, target metric)
    config: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=10, nullable=False)


class Run(UUIDPrimaryKey, Timestamps, Base):
    """One execution attempt of an experiment. Spawns tasks; produces candidates."""

    __tablename__ = "runs"

    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        String(20), default=RunStatus.pending, nullable=False, index=True
    )
    iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)

    # snapshot of resolved config at launch time (repo ref, agents, budgets)
    context: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
