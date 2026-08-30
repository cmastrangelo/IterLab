"""Session + token orchestration on top of an :class:`AuthProvider`.

Access tokens are short-lived JWTs. Refresh tokens are opaque random strings,
stored only as a SHA-256 hash, single-use, and rotated on every refresh. A
replayed (already-rotated) refresh token is treated as a compromise and revokes
every session for that user.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.auth.base import AuthProvider, Credentials
from iterlab.config import get_settings
from iterlab.core.errors import AuthenticationError
from iterlab.core.security import create_access_token, generate_token, hash_token
from iterlab.models.auth_session import AuthSession
from iterlab.models.user import User
from iterlab.schemas.auth import AuthResult, TokenPair
from iterlab.schemas.user import UserOut

logger = logging.getLogger("iterlab.auth")


def _as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat stored timestamps as UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


@dataclass(slots=True)
class ClientInfo:
    user_agent: str | None = None
    ip_address: str | None = None


async def register(
    session: AsyncSession,
    provider: AuthProvider,
    creds: Credentials,
    client: ClientInfo | None = None,
) -> AuthResult:
    if not provider.supports_registration:
        raise AuthenticationError(f"{provider.name} auth does not support registration")
    user = await provider.register(session, creds)
    return await _issue(session, user, client)


async def login(
    session: AsyncSession,
    provider: AuthProvider,
    creds: Credentials,
    client: ClientInfo | None = None,
) -> AuthResult:
    user = await provider.authenticate(session, creds)
    return await _issue(session, user, client)


async def refresh(
    session: AsyncSession,
    refresh_token: str,
    client: ClientInfo | None = None,
) -> AuthResult:
    row = await session.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == hash_token(refresh_token))
    )
    if row is None:
        raise AuthenticationError("invalid refresh token")

    now = datetime.now(UTC)

    if row.revoked_at is not None:
        # token reuse — assume the chain is compromised
        logger.warning("refresh token reuse detected for user %s; revoking sessions", row.user_id)
        await _revoke_all(session, row.user_id, now)
        # persist the revocation even though we are about to raise
        await session.commit()
        raise AuthenticationError("refresh token no longer valid")

    if _as_utc(row.expires_at) <= now:
        raise AuthenticationError("refresh token expired")

    user = await session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("account is unavailable")

    result = await _issue(session, user, client, parent=row)
    return result


async def logout(session: AsyncSession, refresh_token: str) -> None:
    await session.execute(
        update(AuthSession)
        .where(AuthSession.refresh_token_hash == hash_token(refresh_token))
        .where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


# --------------------------------------------------------------------------- #
# internals
# --------------------------------------------------------------------------- #
async def _issue(
    session: AsyncSession,
    user: User,
    client: ClientInfo | None,
    parent: AuthSession | None = None,
) -> AuthResult:
    settings = get_settings()
    client = client or ClientInfo()

    raw_refresh = generate_token()
    new_session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        refresh_token_hash=hash_token(raw_refresh),
        expires_at=datetime.now(UTC) + timedelta(seconds=settings.refresh_token_ttl),
        user_agent=client.user_agent,
        ip_address=client.ip_address,
    )
    session.add(new_session)
    await session.flush()

    if parent is not None:
        parent.revoked_at = datetime.now(UTC)
        parent.rotated_to = new_session.id

    access_token, _ = create_access_token(str(user.id), extra_claims={"sid": str(new_session.id)})

    return AuthResult(
        user=UserOut.model_validate(user),
        tokens=TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_ttl,
        ),
    )


async def _revoke_all(session: AsyncSession, user_id: uuid.UUID, when: datetime) -> None:
    await session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id)
        .where(AuthSession.revoked_at.is_(None))
        .values(revoked_at=when)
    )
