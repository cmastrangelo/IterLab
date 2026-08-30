"""Authentication provider abstraction.

A provider turns credentials into a :class:`~iterlab.models.user.User`. It is
*not* responsible for sessions or tokens — that is ``services.auth_service`` —
so new provider types (OIDC, SAML, API-key-only, ...) stay small.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.models.user import User


@dataclass(slots=True)
class Credentials:
    email: str
    password: str
    full_name: str | None = None


class AuthProvider(abc.ABC):
    name: str = "base"
    #: whether this provider supports self-service registration
    supports_registration: bool = False

    @abc.abstractmethod
    async def register(self, session: AsyncSession, creds: Credentials) -> User: ...

    @abc.abstractmethod
    async def authenticate(self, session: AsyncSession, creds: Credentials) -> User: ...
