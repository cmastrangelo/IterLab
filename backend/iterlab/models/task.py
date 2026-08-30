from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.enums import TaskKind, TaskStatus
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Task(UUIDPrimaryKey, Timestamps, Base):
    """A unit of work dispatched to a worker.

    PostgreSQL holds the durable record; Redis holds the ephemeral ready-queue.
    The two are reconciled by the scheduler (lease expiry -> ``lost`` -> requeue).
    """

    __tablename__ = "tasks"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[TaskKind] = mapped_column(String(20), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(
        String(20), default=TaskStatus.queued, nullable=False, index=True
    )

    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workers.id", ondelete="SET NULL"), index=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # resource request + payload the worker needs to execute
    requirements: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSONMap)
    error: Mapped[str | None] = mapped_column(Text)

    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
