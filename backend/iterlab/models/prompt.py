from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey


class Prompt(UUIDPrimaryKey, Timestamps, Base):
    """A versioned prompt template used by a lab's workflow.

    ``slug`` names a prompt "line" (e.g. ``initial`` vs ``iterate``); ``version``
    increments within ``(lab_id, slug)`` each time the template text changes.
    Run steps reference the exact version they used, so a lab can later compare
    candidate outcomes across prompt versions.
    """

    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint("lab_id", "slug", "version", name="uq_prompts_lab_slug_version"),
    )

    lab_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    digest: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
