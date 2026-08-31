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
    slug: Mapped[str] = mapped_column(String(80), index=True, default="default", nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # hypothesis / objective and constraints (max iterations, budget, target metric)
    config: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    # ordered list of workflow steps: [{handler, name, config}, ...]
    workflow: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    max_iterations: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # provisioned from the lab's instance config (read-only via API)
    managed: Mapped[bool] = mapped_column(default=False, nullable=False)


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
    summary: Mapped[str | None] = mapped_column(Text)

    # primary agent conversation id (e.g. claude --resume <id>), if the workflow
    # ran an agent. Per-step ids are also on RunStep.output.
    agent_session_id: Mapped[str | None] = mapped_column(String(200))

    # snapshot of resolved config at launch time (repo ref, agents, budgets) +
    # accumulated step outputs
    context: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
