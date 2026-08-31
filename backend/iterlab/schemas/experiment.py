from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    # override the workflow's default loop count for this run
    iterations: int | None = Field(default=None, ge=1, le=50)


class ExperimentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lab_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    workflow: dict
    managed: bool
    created_at: datetime


class RunStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iteration: int
    position: int
    handler: str
    name: str | None
    status: str
    output: dict | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None


class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iteration: int
    status: str
    summary: str | None
    commit_sha: str | None
    branch: str | None
    score: float | None
    cost_usd: float | None
    tokens: int | None
    extra: dict


class BenchmarkResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    benchmark_id: uuid.UUID
    score: float | None
    passed: bool | None
    details: dict
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    experiment_id: uuid.UUID
    status: str
    iteration: int
    summary: str | None
    agent_session_id: str | None
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunListItemOut(RunOut):
    """A run plus its candidates + steps — enough to chart each iteration."""

    candidates: list[CandidateOut] = []
    steps: list[RunStepOut] = []
    context: dict = {}


class RunDetailOut(RunOut):
    steps: list[RunStepOut] = []
    candidates: list[CandidateOut] = []
    benchmark_results: list[BenchmarkResultOut] = []
    context: dict = {}
