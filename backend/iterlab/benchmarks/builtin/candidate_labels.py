"""Rank a lab's candidates by a manually-recorded label.

Deployment-agnostic. A benchmark of this kind turns the free-form tags a human
attaches to candidates after the fact (``Candidate.labels``, e.g. a competition
placement, a human-eval grade, a production A/B outcome) into a ranked view.

The workflow never writes these — they come from a person via
``PATCH /candidates/{id}`` or a script. Candidates without the configured
``label_key`` are simply omitted.

Spec::

    label_key: codingame          # required: which key in Candidate.labels
    title: CodinGame Arena
    value_label: League           # column header for the label value
    sort: tiered                  # numeric (default) | tiered | lexical
    order: asc                    # numeric/lexical: asc = smaller is better
    tiers: [Legend, Gold, Silver, Bronze, Wood]   # tiered: best first
    within_tier_order: asc        # tiered: order of the number inside a tier
    baseline_names: [solution_32.py]              # mark these rows as baseline
    extra_entrants:               # fixed reference rows not backed by a candidate
      - { entrant: solution_32.py, value: "Gold 92", baseline: true }
"""

from __future__ import annotations

import math
import re
from typing import Any

from sqlalchemy import select

from iterlab.benchmarks.base import (
    BenchmarkAdapter,
    BenchmarkConfigError,
    BenchmarkContext,
    Leaderboard,
    LeaderboardColumn,
    LeaderboardRow,
)
from iterlab.models.candidate import Candidate
from iterlab.models.experiment import Experiment, Run

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _first_number(text: str) -> float | None:
    m = _NUM.search(text or "")
    return float(m.group()) if m else None


def _entry(entrant: str, value: str, *, local: float | None, source: str | None) -> dict[str, Any]:
    return {"entrant": entrant, "value": value, "local": local, "source": source}


class CandidateLabelsAdapter(BenchmarkAdapter):
    key = "candidate_labels"
    summary = "Rank a lab's candidates by a manually-recorded label (e.g. a competition placement)"

    async def leaderboard(self, ctx: BenchmarkContext) -> Leaderboard:
        spec = ctx.spec
        label_key = spec.get("label_key")
        if not label_key:
            raise BenchmarkConfigError("candidate_labels spec requires 'label_key'")
        lab_id, session = ctx.require_db()

        rows_data: list[dict[str, Any]] = []
        result = await session.execute(
            select(Candidate, Run.iteration)
            .join(Run, Run.id == Candidate.run_id)
            .join(Experiment, Experiment.id == Run.experiment_id)
            .where(Experiment.lab_id == lab_id)
            .order_by(Candidate.created_at)
        )
        for cand, run_iter in result:
            value = (cand.labels or {}).get(label_key)
            if not value:
                continue
            name = (cand.extra or {}).get("name") or cand.summary or f"candidate {str(cand.id)[:8]}"
            rows_data.append(
                _entry(
                    str(name),
                    str(value),
                    local=cand.score,
                    source=f"run #{run_iter} · iter {cand.iteration}",
                )
            )

        for extra in spec.get("extra_entrants", []):
            rows_data.append(
                _entry(
                    str(extra["entrant"]),
                    str(extra["value"]),
                    local=extra.get("local"),
                    source=extra.get("source", "reference"),
                )
            )

        baseline_names = set(spec.get("baseline_names", []))
        baseline_names.update(
            e["entrant"] for e in spec.get("extra_entrants", []) if e.get("baseline")
        )

        keyfn = self._sort_key(spec)
        rows_data.sort(key=lambda d: keyfn(d["value"]))

        has_local = any(d["local"] is not None for d in rows_data)
        rows = [
            LeaderboardRow(
                rank=i,
                entrant=d["entrant"],
                score=d["local"] if isinstance(d["local"], (int, float)) else None,
                is_baseline=d["entrant"] in baseline_names,
                values={
                    "value": d["value"],
                    **({"local": d["local"]} if has_local else {}),
                    "source": d["source"],
                },
            )
            for i, d in enumerate(rows_data, start=1)
        ]

        columns = [
            LeaderboardColumn(
                key="value",
                label=spec.get("value_label", label_key.replace("_", " ").title()),
                kind="string",
                primary=True,
            )
        ]
        if has_local:
            columns.append(
                LeaderboardColumn(
                    key="local",
                    label=spec.get("local_score_label", "Local score"),
                    kind="number",
                )
            )
        columns.append(LeaderboardColumn(key="source", label="Source", kind="string"))

        note = spec.get("note")
        if not rows:
            note = note or f"no candidate has a {label_key!r} label yet"

        return Leaderboard(
            benchmark_slug=spec.get("_slug", "candidate-labels"),
            title=spec.get("title", f"{label_key.replace('_', ' ').title()} ranking"),
            columns=columns,
            rows=rows,
            note=note,
        )

    @staticmethod
    def _sort_key(spec: dict[str, Any]):
        strategy = spec.get("sort", "numeric")
        order = spec.get("order", "asc")
        sign = 1.0 if order == "asc" else -1.0

        if strategy == "lexical":
            def lex(value: str) -> tuple:
                return (value,) if order == "asc" else tuple(-ord(c) for c in value)
            return lex

        if strategy == "tiered":
            tiers = [str(t).lower() for t in spec.get("tiers", [])]
            within = spec.get("within_tier_order", "asc")
            wsign = 1.0 if within == "asc" else -1.0

            def tiered(value: str) -> tuple:
                low = value.strip().lower()
                idx = next(
                    (i for i, t in enumerate(tiers) if low.startswith(t)), len(tiers)
                )
                num = _first_number(value)
                num_key = math.inf if num is None else wsign * num
                return (idx, num_key, value)
            return tiered

        # numeric (default)
        def numeric(value: str) -> tuple:
            num = _first_number(value)
            return (math.inf if num is None else sign * num, value)
        return numeric

    async def health(self, ctx: BenchmarkContext) -> tuple[bool, str]:
        if not ctx.spec.get("label_key"):
            return False, "spec is missing 'label_key'"
        try:
            board = await self.leaderboard(ctx)
        except Exception as err:  # noqa: BLE001
            return False, str(err)
        return True, f"ok — {len(board.rows)} labelled candidate(s)"
