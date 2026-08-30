from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Agent(UUIDPrimaryKey, Timestamps, Base):
    """An LLM agent/model configuration.

    Provider-agnostic: ``provider`` + ``model`` name the backing model, ``params``
    holds provider-specific knobs, ``tools`` the enabled tool set. A provider
    registry (future) resolves ``provider`` to an implementation.
    """

    __tablename__ = "agents"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. "anthropic"
    model: Mapped[str] = mapped_column(String(200), nullable=False)    # e.g. "claude-sonnet-5"
    params: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    tools: Mapped[list] = mapped_column(JSONMap, default=list, nullable=False)

    # reference to the API-key secret, resolved at dispatch time
    credential_ref: Mapped[str | None] = mapped_column(String(200))
