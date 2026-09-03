from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from iterlab.schemas.benchmark import BenchmarkOut


class LabCreate(BaseModel):
    project_id: uuid.UUID
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$")
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    repo_url: str | None = Field(default=None, max_length=500)
    repo_default_branch: str = "main"
    settings: dict = Field(default_factory=dict)


class LabOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    repo_url: str | None
    repo_default_branch: str
    settings: dict
    prompt_bindings: dict | None = None
    source: str
    created_at: datetime


class LabDetailOut(LabOut):
    benchmarks: list[BenchmarkOut] = Field(default_factory=list)
