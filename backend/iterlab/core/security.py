"""Security primitives: password hashing, opaque tokens, and JWT access tokens.

Kept deliberately small and dependency-light so the auth layer can be swapped
without dragging crypto choices along.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from iterlab.config import get_settings

_ph = PasswordHasher()


# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


# --------------------------------------------------------------------------- #
# Opaque tokens (refresh tokens, worker tokens, API keys)
# --------------------------------------------------------------------------- #
def generate_token(nbytes: int = 48) -> str:
    """Return a URL-safe random secret. Store only its hash."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Deterministic hash for at-rest storage / lookup of opaque tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


# --------------------------------------------------------------------------- #
# JWT access tokens
# --------------------------------------------------------------------------- #
def create_access_token(
    subject: str,
    *,
    expires_in: int | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=expires_in or settings.access_token_ttl)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expire


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.PyJWTError subclasses on any problem."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload
