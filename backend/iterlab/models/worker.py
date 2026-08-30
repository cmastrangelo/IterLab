from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.enums import WorkerStatus
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Worker(UUIDPrimaryKey, Timestamps, Base):
    """A registered executor.

    Workers authenticate with their own token (hash stored here), heartbeat
    periodically, and advertise resources. The controller assigns tasks; it
    never runs experiment code itself.
    """

    __tablename__ = "workers"

    # optional: which user registered this worker (multi-tenant later)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    status: Mapped[WorkerStatus] = mapped_column(
        String(20), default=WorkerStatus.offline, nullable=False, index=True
    )
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # advertised capacity: {"cpu": 8, "memory_mb": 32000, "gpu": 1, "vram_mb": 24000, ...}
    resources: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    # free capacity right now
    resources_available: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    # arbitrary labels for scheduling constraints
    labels: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)

    agent_version: Mapped[str | None] = mapped_column(String(40))
