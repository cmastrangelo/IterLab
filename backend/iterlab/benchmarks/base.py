"""Benchmark adapter interface and shared result types."""

from __future__ import annotations

import abc
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LeaderboardColumn(BaseModel):
    key: str
    label: str
    kind: str = "number"  # "number" | "string" | "percent" | "integer"
    primary: bool = False  # the column the leaderboard is ranked by


class LeaderboardRow(BaseModel):
    rank: int
    entrant: str
    score: float | None = None
    is_baseline: bool = False
    is_candidate: bool = False  # the row for the candidate under evaluation
    values: dict[str, Any] = Field(default_factory=dict)


class Leaderboard(BaseModel):
    benchmark_slug: str
    title: str
    columns: list[LeaderboardColumn]
    rows: list[LeaderboardRow]
    updated_at: datetime | None = None
    note: str | None = None


@dataclass(slots=True)
class BenchmarkContext:
    """Everything an adapter needs beyond its own ``spec``.

    ``spec`` is the benchmark's stored configuration. ``resolve_secret`` turns a
    ``"SOMENAME_env"`` style reference in the spec into the actual value, read
    from the process environment (which the instance ``.env`` populates). This
    keeps real DSNs / credentials out of the database and the repo.
    """

    spec: dict[str, Any]

    def resolve_secret(self, ref: str | None, *, required: bool = True) -> str | None:
        if not ref:
            if required:
                raise BenchmarkConfigError("missing secret reference")
            return None
        value = os.environ.get(ref)
        if value is None and required:
            raise BenchmarkConfigError(
                f"environment variable {ref!r} is not set (expected via instance .env)"
            )
        return value


class BenchmarkError(RuntimeError):
    """Adapter failed to produce a result."""


class BenchmarkConfigError(BenchmarkError):
    """The benchmark spec is missing or malformed."""


class BenchmarkAdapter(abc.ABC):
    #: registry key; also the value stored in ``Benchmark.adapter``
    key: str = "base"
    #: human description shown in the UI / API
    summary: str = ""

    @abc.abstractmethod
    async def leaderboard(self, ctx: BenchmarkContext) -> Leaderboard:
        """Return the benchmark's current standings."""

    async def health(self, ctx: BenchmarkContext) -> tuple[bool, str]:
        """Cheap reachability check. Default: try to build the leaderboard."""
        try:
            await self.leaderboard(ctx)
            return True, "ok"
        except Exception as err:  # noqa: BLE001
            return False, str(err)
