from __future__ import annotations

from fastapi import APIRouter, status

from iterlab.api.deps import ClientInfoDep, CurrentUser, SessionDep
from iterlab.auth import get_auth_provider
from iterlab.auth.base import Credentials
from iterlab.schemas.auth import (
    AuthResult,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
)
from iterlab.schemas.user import UserOut
from iterlab.services import auth_service

router = APIRouter()

# Single active provider for now; deployment modes can make this configurable.
_provider = get_auth_provider("local")


@router.post(
    "/register",
    response_model=AuthResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and start a session",
)
async def register(body: RegisterRequest, session: SessionDep, client: ClientInfoDep) -> AuthResult:
    creds = Credentials(email=body.email, password=body.password, full_name=body.full_name)
    return await auth_service.register(session, _provider, creds, client)


@router.post("/login", response_model=AuthResult, summary="Exchange credentials for tokens")
async def login(body: LoginRequest, session: SessionDep, client: ClientInfoDep) -> AuthResult:
    creds = Credentials(email=body.email, password=body.password)
    return await auth_service.login(session, _provider, creds, client)


@router.post("/refresh", response_model=AuthResult, summary="Rotate a refresh token")
async def refresh(body: RefreshRequest, session: SessionDep, client: ClientInfoDep) -> AuthResult:
    return await auth_service.refresh(session, body.refresh_token, client)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a refresh token",
)
async def logout(body: RefreshRequest, session: SessionDep) -> None:
    await auth_service.logout(session, body.refresh_token)


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
