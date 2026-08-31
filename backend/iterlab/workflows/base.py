"""Step handler interface + the context/result passed across a run's steps."""

from __future__ import annotations

import abc
import logging
import os
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StepContext:
    """What a step handler receives.

    ``outputs`` accumulates prior steps' ``StepResult.output`` dicts, keyed by
    step handler name (and also by ``position`` as a string), so a later step
    can read e.g. ``ctx.outputs["locm_new_solution"]["solution_name"]``.
    """

    run_id: uuid.UUID
    lab: dict[str, Any]  # {id, slug, name, repo_url, settings, ...}
    experiment: dict[str, Any]  # {id, slug, name, config}
    step_config: dict[str, Any]
    # 0-based loop index within the run (0 for a single-pass workflow)
    iteration: int = 0
    # this iteration's completed step outputs, keyed by handler
    outputs: dict[str, Any] = field(default_factory=dict)
    # prior iterations' step outputs: history[i][handler] -> output
    history: list[dict[str, Any]] = field(default_factory=list)
    # the run's agent conversation id, if one has been started (carries across
    # iterations so a resuming agent step can continue the same conversation)
    agent_session_id: str | None = None
    # agents available to the deployment, keyed by name: {name: {kind, cli|api, ...}}
    agents: dict[str, Any] = field(default_factory=dict)
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("iterlab.step"))
    # persist partial progress mid-step (e.g. an agent session id before the
    # agent finishes). Merged into the step's recorded output; an
    # ``agent_session_id`` key is promoted to the run immediately.
    checkpoint: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    def agent(self, name: str | None) -> dict[str, Any] | None:
        return self.agents.get(name) if name else None

    async def save(self, output: dict[str, Any]) -> None:
        if self.checkpoint is not None:
            await self.checkpoint(output)

    def resolve_secret(self, ref: str | None, *, required: bool = True) -> str | None:
        if not ref:
            if required:
                raise StepError("missing secret reference")
            return None
        value = os.environ.get(ref)
        if value is None and required:
            raise StepError(f"env var {ref!r} is not set (expected via instance .env)")
        return value


@dataclass(slots=True)
class CandidateInfo:
    name: str | None = None            # e.g. "solution_54.py"
    summary: str | None = None
    commit_sha: str | None = None
    branch: str | None = None
    score: float | None = None
    cost_usd: float | None = None
    tokens: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BenchmarkOutcome:
    benchmark_slug: str
    score: float | None = None
    passed: bool | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PromptRef:
    """A prompt template a step used. The executor versions it per (lab, slug)."""

    slug: str            # prompt "line", e.g. "initial" / "iterate"
    template: str        # the versioned text (may contain {placeholders})
    rendered: str | None = None  # what was actually sent, for the record


@dataclass(slots=True)
class StepResult:
    output: dict[str, Any] = field(default_factory=dict)
    # promoted to first-class columns by the executor when present:
    agent_session_id: str | None = None
    candidate: CandidateInfo | None = None
    benchmarks: list[BenchmarkOutcome] = field(default_factory=list)
    prompt: PromptRef | None = None
    summary: str | None = None


class StepError(RuntimeError):
    """A step handler failed. ``output``/``agent_session_id`` are recorded anyway."""

    def __init__(
        self,
        message: str,
        *,
        output: dict[str, Any] | None = None,
        agent_session_id: str | None = None,
    ):
        super().__init__(message)
        self.output = output or {}
        self.agent_session_id = agent_session_id


class StepHandler(abc.ABC):
    key: str = "base"
    summary: str = ""

    @abc.abstractmethod
    async def run(self, ctx: StepContext) -> StepResult: ...
