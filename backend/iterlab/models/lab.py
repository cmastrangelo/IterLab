from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Lab(UUIDPrimaryKey, Timestamps, Base):
    """A workspace inside a project: a connected repo + an agent roster + settings."""

    __tablename__ = "labs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # connected external repository
    repo_url: Mapped[str | None] = mapped_column(String(500))
    repo_default_branch: Mapped[str] = mapped_column(String(200), default="main", nullable=False)
    # reference to a secret (token) held elsewhere — never the secret itself
    repo_credential_ref: Mapped[str | None] = mapped_column(String(200))

    # free-form lab configuration (goal prompt, test command, budgets, ...)
    settings: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)

    # {prompt_slug: active_version_int} — which immutable prompt version each of
    # the lab's prompt "lines" currently resolves to. Prompt text lives in
    # registered, content-hashed Prompt rows; this is the only movable knob.
    prompt_bindings: Mapped[dict | None] = mapped_column(JSONMap)

    # "manual" (created via the API/UI) or "instance" (provisioned from this
    # deployment's private instance config, and read-only via the API).
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)


class LabAgent(UUIDPrimaryKey, Timestamps, Base):
    """Association: an agent config assigned to a lab, with a per-lab weight/role."""

    __tablename__ = "lab_agents"

    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str | None] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(default=True, nullable=False)
