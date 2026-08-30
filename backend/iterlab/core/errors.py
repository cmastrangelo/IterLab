"""Typed application errors and their HTTP mapping."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str | None = None, *, code: str | None = None):
        self.message = message or self.__class__.__doc__ or "error"
        if code:
            self.code = code
        super().__init__(self.message)


class NotFoundError(APIError):
    """Resource not found."""

    status_code = 404
    code = "not_found"


class ConflictError(APIError):
    """Resource already exists."""

    status_code = 409
    code = "conflict"


class AuthenticationError(APIError):
    """Authentication failed."""

    status_code = 401
    code = "unauthenticated"


class PermissionError_(APIError):
    """Not permitted."""

    status_code = 403
    code = "forbidden"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _handle_api_error(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )
