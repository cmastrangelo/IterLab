from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_SLUG = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"


class StepSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    handler: str  # step handler registry key
    name: str | None = None
    config: dict = Field(default_factory=dict)


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=_SLUG, default="default")
    name: str = "default"
    description: str | None = None
    # how many times to repeat the whole step list per run. Each iteration
    # produces its own candidate; a run's context (e.g. an agent conversation
    # id) carries across iterations.
    iterations: int = Field(default=1, ge=1, le=50)
    steps: list[StepSpec] = Field(default_factory=list)
