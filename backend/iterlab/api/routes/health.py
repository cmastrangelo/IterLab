from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from iterlab import __version__
from iterlab.api.deps import SessionDep
from iterlab.queues import get_backend

router = APIRouter()


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict:
    return {"status": "ok", "version": __version__}


@router.get("/readyz", summary="Readiness probe (checks Postgres + Redis)")
async def readyz(session: SessionDep, response: Response) -> dict:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as err:  # noqa: BLE001
        checks["postgres"] = f"error: {err}"

    backend = get_backend()
    try:
        await backend.ping()
        checks["redis"] = "ok"
    except Exception as err:  # noqa: BLE001
        checks["redis"] = f"error: {err}"
    finally:
        await backend.close()

    ready = all(v == "ok" for v in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ready" if ready else "degraded", "checks": checks}
