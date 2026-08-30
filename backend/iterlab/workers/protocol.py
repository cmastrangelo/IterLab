"""Worker <-> controller wire protocol.

Transport-agnostic Pydantic models. The reference implementation is HTTP+JSON
(see ``api/routes/workers.py`` and the ``worker/`` package); the same models
could ride gRPC or a message bus later.

Lifecycle:

    register  -> {worker_id, worker_token}
    heartbeat -> (every N seconds) advertise resources + current task status
    pull      -> receive the next assigned TaskAssignment (or nothing)
    result    -> report terminal outcome + candidate + artifact refs
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PROTOCOL_VERSION = "0.1"


class WorkerResources(BaseModel):
    cpu: float = Field(0, description="logical CPU cores")
    memory_mb: int = 0
    gpu: int = 0
    vram_mb: int = 0
    disk_mb: int = 0
    extra: dict = Field(default_factory=dict)


class RegisterRequest(BaseModel):
    name: str
    protocol_version: str = PROTOCOL_VERSION
    agent_version: str | None = None
    resources: WorkerResources = Field(default_factory=WorkerResources)
    labels: dict = Field(default_factory=dict)


class RegisterResponse(BaseModel):
    worker_id: uuid.UUID
    worker_token: str
    heartbeat_interval_s: int = 15


class TaskStatusReport(BaseModel):
    task_id: uuid.UUID
    status: Literal["running", "succeeded", "failed", "cancelled"]
    progress: float | None = None
    message: str | None = None


class HeartbeatRequest(BaseModel):
    resources_available: WorkerResources = Field(default_factory=WorkerResources)
    status: Literal["idle", "busy", "draining"] = "idle"
    tasks: list[TaskStatusReport] = Field(default_factory=list)


class HeartbeatResponse(BaseModel):
    ok: bool = True
    # controller-initiated instructions (cancel a task, drain, reconfigure)
    directives: list[dict] = Field(default_factory=list)
    server_time: datetime


class TaskAssignment(BaseModel):
    task_id: uuid.UUID
    run_id: uuid.UUID
    kind: str
    payload: dict = Field(default_factory=dict)
    requirements: dict = Field(default_factory=dict)
    lease_expires_at: datetime | None = None


class ArtifactRef(BaseModel):
    kind: str = "other"
    name: str
    storage_backend: str
    storage_key: str
    content_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None


class CandidateReport(BaseModel):
    parent_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    iteration: int = 0
    summary: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    score: float | None = None
    cost_usd: float | None = None
    tokens: int | None = None
    metrics: dict = Field(default_factory=dict)


class TaskResultRequest(BaseModel):
    task_id: uuid.UUID
    status: Literal["succeeded", "failed", "cancelled"]
    error: str | None = None
    candidate: CandidateReport | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
