from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentGrade(BaseModel):
    """How an agent has done, graded against the frontier it faced.

    ``avg_delta`` is the average, across this agent's runs, of
    ``best score the run produced − best score that existed before the run
    started``. Positive means it tends to advance the lab's best candidate;
    negative means it tends to fall short of what already existed.
    """

    agent: str
    runs: int
    candidates: int
    avg_score: float
    avg_delta: float | None
    best_delta: float | None
    new_best_rate: float  # fraction of this agent's runs that set a new all-time best
    avg_cost_usd: float | None
    last_used: datetime


class PromptGrade(BaseModel):
    """How a prompt version has done, graded against its own job.

    A prompt only used at iteration 0 ("cold start") is graded like an agent —
    frontier delta. A prompt only used at iteration >0 ("iterate") is graded on
    within-run lift: how much it improved on its own run's iteration-0 score.
    ``basis`` says which (or "mixed" if a prompt saw both).
    """

    prompt_id: uuid.UUID
    slug: str
    version: int
    uses: int
    basis: str  # "cold start" | "iterate lift" | "mixed" | "—"
    avg_score: float
    avg_delta: float | None
    best_delta: float | None
    new_best_rate: float
    avg_cost_usd: float | None


class LabGrades(BaseModel):
    agents: list[AgentGrade]
    prompts: list[PromptGrade]
    note: str
