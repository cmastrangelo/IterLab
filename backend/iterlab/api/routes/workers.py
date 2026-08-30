"""Worker <-> controller HTTP endpoints (reference transport for the protocol).

Scope for this phase: a worker can register, receive a token, and heartbeat.
Task dispatch returns empty until the scheduler loop is implemented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import AuthenticationError
from iterlab.core.security import generate_token, hash_token
from iterlab.models.enums import WorkerStatus
from iterlab.models.worker import Worker
from iterlab.workers.protocol import (
    HeartbeatRequest,
    HeartbeatResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter()

_worker_bearer = HTTPBearer(auto_error=False)


async def authenticated_worker(
    worker_id: uuid.UUID,
    session: SessionDep,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_worker_bearer)],
) -> Worker:
    if creds is None:
        raise AuthenticationError("missing worker token")
    worker = await session.get(Worker, worker_id)
    if worker is None or worker.token_hash != hash_token(creds.credentials):
        raise AuthenticationError("invalid worker credentials")
    return worker


AuthedWorker = Annotated[Worker, Depends(authenticated_worker)]


@router.get("", summary="List workers")
async def list_workers(user: CurrentUser, session: SessionDep) -> list[dict]:
    rows = await session.scalars(select(Worker).order_by(Worker.created_at.desc()))
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "status": w.status,
            "resources": w.resources,
            "resources_available": w.resources_available,
            "labels": w.labels,
            "last_heartbeat_at": w.last_heartbeat_at,
            "agent_version": w.agent_version,
        }
        for w in rows
    ]


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a worker and receive a worker token",
)
async def register_worker(
    body: RegisterRequest, user: CurrentUser, session: SessionDep
) -> RegisterResponse:
    raw_token = generate_token()
    worker = Worker(
        owner_id=user.id,
        name=body.name,
        token_hash=hash_token(raw_token),
        status=WorkerStatus.online,
        last_heartbeat_at=datetime.now(UTC),
        resources=body.resources.model_dump(),
        resources_available=body.resources.model_dump(),
        labels=body.labels,
        agent_version=body.agent_version,
    )
    session.add(worker)
    await session.flush()
    return RegisterResponse(worker_id=worker.id, worker_token=raw_token)


@router.post(
    "/{worker_id}/heartbeat",
    response_model=HeartbeatResponse,
    summary="Report liveness, resources, and task status",
)
async def heartbeat(
    body: HeartbeatRequest, worker: AuthedWorker, session: SessionDep
) -> HeartbeatResponse:
    worker.last_heartbeat_at = datetime.now(UTC)
    worker.resources_available = body.resources_available.model_dump()
    worker.status = {
        "idle": WorkerStatus.idle,
        "busy": WorkerStatus.busy,
        "draining": WorkerStatus.draining,
    }[body.status]
    await session.flush()
    return HeartbeatResponse(server_time=datetime.now(UTC))


@router.get(
    "/{worker_id}/tasks",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Pull the next assigned task (none until the scheduler loop lands)",
)
async def pull_task(worker: AuthedWorker) -> None:
    return None
