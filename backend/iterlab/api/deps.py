"""Shared FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.core.errors import AuthenticationError
from iterlab.core.security import decode_access_token
from iterlab.db.session import get_session
from iterlab.models.user import User
from iterlab.services.auth_service import ClientInfo

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)


def get_client_info(request: Request) -> ClientInfo:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else None)
    return ClientInfo(user_agent=request.headers.get("user-agent"), ip_address=ip)


ClientInfoDep = Annotated[ClientInfo, Depends(get_client_info)]


async def get_current_user(
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if creds is None:
        raise AuthenticationError("missing bearer token")
    try:
        payload = decode_access_token(creds.credentials)
    except jwt.PyJWTError as err:
        raise AuthenticationError("invalid or expired token") from err

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as err:
        raise AuthenticationError("malformed token subject") from err

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("account is unavailable")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
