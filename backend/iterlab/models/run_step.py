from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class RunStep(UUIDPrimaryKey, Timestamps, Base):
    """One step of a run's workflow, and its recorded outcome.

    ``output`` is a free-form dict the step handler returns — for an agent step
    it typically holds the agent's conversation/session id and a summary; for a
    benchmark step, the resolved scores.
    """

    __tablename__ = "run_steps"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # 0-based workflow loop index; 0 for a single-pass workflow
    iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    handler: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    config: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    output: Mapped[dict | None] = mapped_column(JSONMap)
    error: Mapped[str | None] = mapped_column(Text)

    # the versioned prompt this step used, when it ran an agent
    prompt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("prompts.id", ondelete="SET NULL"), index=True
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
