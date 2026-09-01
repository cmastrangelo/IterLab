"""Grade agents and prompts by how they moved a lab's frontier.

Not a benchmark (those rank *candidates*). This ranks the upstream choices —
which agent, which prompt version — that tend to produce good candidates,
graded against what each was actually asked to do:

- An **agent**'s job, each run, is to beat what already exists. Grade =
  ``best score the run produced − best score that existed before the run
  started`` (the run's "frontier delta"), averaged across its runs.
- A prompt used at **iteration 0** ("cold start") has the same job — same
  metric.
- A prompt used at **iteration > 0** ("iterate") has a different job: make the
  *next* attempt beat the run's own iteration 0. Grade = average
  ``score(iter k) − score(iter 0 of the same run)``, i.e. within-run lift.

Both also get a "new-best rate" — how often they produced the lab's new
all-time-best candidate — which is the plain yes/no version of the same idea.

Everything here is generic: it reads ``Candidate.score`` (whatever a lab's
benchmarks resolve it to) and the agent name a step recorded in its output
(the same ``output["agent"]`` convention the Experiments UI already reads),
so it works for any lab without per-lab configuration.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.models.candidate import Candidate
from iterlab.models.experiment import Experiment, Run
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.schemas.grades import AgentGrade, LabGrades, PromptGrade

_SAMPLE_NOTE = (
    "Every group here is a small sample (often 1-3 runs). Read these as "
    "directional signal, not statistically significant rankings."
)


def _round(x: float | None, n: int = 2) -> float | None:
    return round(x, n) if x is not None else None


async def compute_lab_grades(session: AsyncSession, lab_id: uuid.UUID) -> LabGrades:
    runs = list(
        await session.scalars(
            select(Run)
            .join(Experiment, Experiment.id == Run.experiment_id)
            .where(Experiment.lab_id == lab_id)
            .order_by(Run.created_at)
        )
    )
    if not runs:
        return LabGrades(agents=[], prompts=[], note="no runs yet")
    run_ids = [r.id for r in runs]

    candidates = list(
        await session.scalars(
            select(Candidate)
            .where(Candidate.run_id.in_(run_ids), Candidate.score.is_not(None))
            .order_by(Candidate.iteration)
        )
    )
    steps = list(await session.scalars(select(RunStep).where(RunStep.run_id.in_(run_ids))))

    prompt_ids = {s.prompt_id for s in steps if s.prompt_id is not None}
    prompts_by_id: dict[uuid.UUID, Prompt] = {}
    if prompt_ids:
        prompts_by_id = {
            p.id: p for p in await session.scalars(select(Prompt).where(Prompt.id.in_(prompt_ids)))
        }

    # (run_id, iteration) -> the step that used a prompt (= "the agent step")
    agent_step: dict[tuple[uuid.UUID, int], RunStep] = {}
    for s in steps:
        if s.prompt_id is not None:
            agent_step[(s.run_id, s.iteration)] = s
    # agent name per run: the display name a CLI step recorded in its output,
    # same convention the Experiments "Agent" column reads
    run_agent: dict[uuid.UUID, str] = {}
    for s in steps:
        name = (s.output or {}).get("agent") if isinstance(s.output, dict) else None
        if name and s.run_id not in run_agent:
            run_agent[s.run_id] = name

    by_run: dict[uuid.UUID, list[Candidate]] = defaultdict(list)
    for c in candidates:
        by_run[c.run_id].append(c)
    for lst in by_run.values():
        lst.sort(key=lambda c: c.iteration)

    agent_acc: dict[str, dict] = defaultdict(
        lambda: {"runs": 0, "scores": [], "deltas": [], "costs": [], "new_best": 0, "last": None}
    )
    prompt_acc: dict[uuid.UUID, dict] = defaultdict(
        lambda: {
            "uses": 0, "scores": [], "costs": [], "new_best": 0,
            "cold_deltas": [], "iter_deltas": [],
        }
    )

    frontier: float | None = None  # best score across all *prior* runs
    lab_best_ever: float | None = None  # best score across all candidates seen so far

    # queried with score IS NOT NULL, so this is total for every candidate here
    score: dict[uuid.UUID, float] = {c.id: c.score for c in candidates if c.score is not None}

    for run in runs:
        cands = by_run.get(run.id)
        if not cands:
            continue
        run_best = max(score[c.id] for c in cands)
        run_delta = None if frontier is None else run_best - frontier
        run_is_new_best = frontier is None or run_best > frontier

        agent_name = run_agent.get(run.id, "unknown")
        acc = agent_acc[agent_name]
        acc["runs"] += 1
        acc["scores"].extend(score[c.id] for c in cands)
        acc["costs"].extend(c.cost_usd for c in cands if c.cost_usd is not None)
        if run_delta is not None:
            acc["deltas"].append(run_delta)
        if run_is_new_best:
            acc["new_best"] += 1
        acc["last"] = run.created_at

        iter0 = next((c for c in cands if c.iteration == 0), None)
        iter0_score = score[iter0.id] if iter0 is not None else None

        for c in cands:
            step = agent_step.get((run.id, c.iteration))
            if step is None or step.prompt_id is None:
                continue
            cand_score = score[c.id]
            pacc = prompt_acc[step.prompt_id]
            pacc["uses"] += 1
            pacc["scores"].append(cand_score)
            if c.cost_usd is not None:
                pacc["costs"].append(c.cost_usd)
            is_new_best_ever = lab_best_ever is None or cand_score > lab_best_ever
            if is_new_best_ever:
                pacc["new_best"] += 1
            if c.iteration == 0:
                if frontier is not None:
                    pacc["cold_deltas"].append(cand_score - frontier)
            elif iter0_score is not None:
                pacc["iter_deltas"].append(cand_score - iter0_score)
            lab_best_ever = (
                cand_score if lab_best_ever is None else max(lab_best_ever, cand_score)
            )

        frontier = run_best if frontier is None else max(frontier, run_best)

    agents_out = [
        AgentGrade(
            agent=name,
            runs=acc["runs"],
            candidates=len(acc["scores"]),
            avg_score=_round(mean(acc["scores"])),  # type: ignore[arg-type]
            avg_delta=_round(mean(acc["deltas"])) if acc["deltas"] else None,
            best_delta=_round(max(acc["deltas"])) if acc["deltas"] else None,
            new_best_rate=_round(acc["new_best"] / acc["runs"]),  # type: ignore[arg-type]
            avg_cost_usd=_round(mean(acc["costs"])) if acc["costs"] else None,
            last_used=acc["last"],
        )
        for name, acc in agent_acc.items()
    ]
    agents_out.sort(key=lambda a: (a.avg_delta is None, -(a.avg_delta or 0.0)))

    prompts_out: list[PromptGrade] = []
    for pid, acc in prompt_acc.items():
        p = prompts_by_id.get(pid)
        if p is None:
            continue
        cold, itr = acc["cold_deltas"], acc["iter_deltas"]
        if cold and itr:
            basis, deltas = "mixed", cold + itr
        elif cold:
            basis, deltas = "cold start", cold
        elif itr:
            basis, deltas = "iterate lift", itr
        else:
            basis, deltas = "—", []
        prompts_out.append(
            PromptGrade(
                prompt_id=pid,
                slug=p.slug,
                version=p.version,
                uses=acc["uses"],
                basis=basis,
                avg_score=_round(mean(acc["scores"])),  # type: ignore[arg-type]
                avg_delta=_round(mean(deltas)) if deltas else None,
                best_delta=_round(max(deltas)) if deltas else None,
                new_best_rate=_round(acc["new_best"] / acc["uses"]),  # type: ignore[arg-type]
                avg_cost_usd=_round(mean(acc["costs"])) if acc["costs"] else None,
            )
        )
    prompts_out.sort(key=lambda p: (p.slug, p.avg_delta is None, -(p.avg_delta or 0.0)))

    return LabGrades(agents=agents_out, prompts=prompts_out, note=_SAMPLE_NOTE)
