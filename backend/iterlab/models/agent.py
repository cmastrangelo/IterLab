from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Agent(UUIDPrimaryKey, Timestamps, Base):
    """An LLM agent configuration.

    ``kind`` selects how the agent is driven:

    * ``"cli"`` — a local command (e.g. ``claude``) run by a worker. ``params``
      holds ``{command, args, working_dir, env}``. Auth is the CLI's own.
    * ``"api"`` — a hosted model API. ``provider`` + ``model`` name it,
      ``credential_ref`` names the env var holding the key, ``params`` holds
      request knobs.

    Agents are executed on **workers**, never by the controller.
    """

    __tablename__ = "agents"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # "cli" | "api"
    kind: Mapped[str] = mapped_column(String(20), default="api", nullable=False)

    # api kind: provider name, e.g. "anthropic"
    provider: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    model: Mapped[str | None] = mapped_column(String(200))  # e.g. "claude-sonnet-5"
    credential_ref: Mapped[str | None] = mapped_column(String(200))  # env var name for the API key

    # kind-specific config (cli: command/args/working_dir/env; api: temperature/...)
    params: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
    tools: Mapped[list] = mapped_column(JSONMap, default=list, nullable=False)

    # provisioned from instance config (read-only via API)
    managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
