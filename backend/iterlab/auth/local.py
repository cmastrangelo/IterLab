"""Local email + password authentication."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.auth.base import AuthProvider, Credentials
from iterlab.core.errors import AuthenticationError, ConflictError
from iterlab.core.security import (
    hash_password,
    password_needs_rehash,
    verify_password,
)
from iterlab.models.user import User


class LocalAuthProvider(AuthProvider):
    name = "local"
    supports_registration = True

    async def register(self, session: AsyncSession, creds: Credentials) -> User:
        email = creds.email.strip().lower()
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise ConflictError("an account with that email already exists")

        user = User(
            email=email,
            full_name=creds.full_name,
            password_hash=hash_password(creds.password),
        )
        session.add(user)
        await session.flush()
        return user

    async def authenticate(self, session: AsyncSession, creds: Credentials) -> User:
        email = creds.email.strip().lower()
        user = await session.scalar(select(User).where(User.email == email))

        # Verify even when the user is missing to keep timing uniform.
        reference_hash = user.password_hash if user else _DUMMY_HASH
        ok = verify_password(creds.password, reference_hash)

        if user is None or not ok:
            raise AuthenticationError("invalid email or password")
        if not user.is_active:
            raise AuthenticationError("account is disabled")

        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(creds.password)
            await session.flush()

        return user


# Precomputed argon2 hash of a random string — used for constant-time rejection
# of unknown accounts.
_DUMMY_HASH = hash_password("iterlab-timing-equalizer-not-a-real-password")
