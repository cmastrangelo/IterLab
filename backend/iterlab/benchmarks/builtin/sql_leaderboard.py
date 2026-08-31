"""Generic leaderboard benchmark backed by an arbitrary SQL query.

Deployment-agnostic: it knows nothing about any particular schema. The instance
lab config supplies the DSN (by env-var reference) and the ``SELECT`` that
returns one row per entrant. Used by the IterLab reference deployment to surface
an external Elo/win-rate ladder, but usable for any ranked table.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

import asyncpg

from iterlab.benchmarks.base import (
    BenchmarkAdapter,
    BenchmarkConfigError,
    BenchmarkContext,
    BenchmarkError,
    Leaderboard,
    LeaderboardColumn,
    LeaderboardRow,
)


def _infer_kind(value: Any) -> str:
    if isinstance(value, bool):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


class SqlLeaderboardAdapter(BenchmarkAdapter):
    key = "sql_leaderboard"
    summary = "Ranked leaderboard from a SQL query against an external database"

    async def leaderboard(self, ctx: BenchmarkContext) -> Leaderboard:
        spec = ctx.spec
        dsn = ctx.resolve_secret(spec.get("dsn_env"))
        query = spec.get("query")
        if not query:
            raise BenchmarkConfigError("sql_leaderboard spec requires 'query'")

        entrant_col = spec.get("entrant_column", "entrant")
        score_col = spec.get("score_column")
        baseline_col = spec.get("baseline_column")
        updated_at_query = spec.get("updated_at_query")
        timeout = float(spec.get("timeout_seconds", 15))

        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=timeout)
        except (TimeoutError, OSError, asyncpg.PostgresError) as err:
            raise BenchmarkError(f"could not connect to leaderboard database: {err}") from err

        try:
            records = await conn.fetch(query, timeout=timeout)
            updated_at: datetime | None = None
            if updated_at_query:
                updated_at = await conn.fetchval(updated_at_query, timeout=timeout)
        except asyncpg.PostgresError as err:
            raise BenchmarkError(f"leaderboard query failed: {err}") from err
        finally:
            await conn.close()

        rows: list[LeaderboardRow] = []
        for i, rec in enumerate(records, start=1):
            data = dict(rec)
            if entrant_col not in data:
                raise BenchmarkConfigError(
                    f"entrant_column {entrant_col!r} not in query result columns {list(data)}"
                )
            entrant = str(data.pop(entrant_col))
            score = data.get(score_col) if score_col else None
            is_baseline = bool(data.get(baseline_col)) if baseline_col else False
            rows.append(
                LeaderboardRow(
                    rank=i,
                    entrant=entrant,
                    score=float(score) if isinstance(score, (int, float)) else None,
                    is_baseline=is_baseline,
                    values=data,
                )
            )

        columns = self._columns(spec, records[0] if records else None, score_col, baseline_col)
        return Leaderboard(
            benchmark_slug=spec.get("_slug", "leaderboard"),
            title=spec.get("title", "Leaderboard"),
            columns=columns,
            rows=rows,
            updated_at=updated_at,
            note=spec.get("note"),
        )

    @staticmethod
    def _columns(spec, sample, score_col, baseline_col) -> list[LeaderboardColumn]:
        if spec.get("columns"):
            return [LeaderboardColumn(**c) for c in spec["columns"]]
        if sample is None:
            return []
        entrant_col = spec.get("entrant_column", "entrant")
        cols: list[LeaderboardColumn] = []
        for key in sample:
            if key in (entrant_col, baseline_col):
                continue
            cols.append(
                LeaderboardColumn(
                    key=key,
                    label=key.replace("_", " ").title(),
                    kind=_infer_kind(sample[key]),
                    primary=(key == score_col),
                )
            )
        return cols
