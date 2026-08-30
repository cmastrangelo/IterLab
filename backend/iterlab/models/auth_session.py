from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey


class AuthSession(UUIDPrimaryKey, Timestamps, Base):
    """A refresh-token-backed login session.

    The refresh token itself is never stored — only its SHA-256 hash. Tokens are
    rotated on use (``rotated_to``) so a replayed old token can be detected and
    the whole chain revoked.
    """

    __tablename__ = "auth_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("auth_sessions.id", ondelete="SET NULL")
    )

    # lightweight client fingerprint for the "your sessions" UI later
    user_agent: Mapped[str | None] = mapped_column(String(400))
    ip_address: Mapped[str | None] = mapped_column(String(64))

    @property
    def is_active(self) -> bool:
        from datetime import UTC

        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return self.revoked_at is None and expires > datetime.now(UTC)
