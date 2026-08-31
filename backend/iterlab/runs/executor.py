"""Execute a run: iterate its workflow steps, dispatch each to a step handler,
and record steps / candidate / benchmark results."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.models.agent import Agent
from iterlab.models.benchmark import Benchmark, BenchmarkResult
from iterlab.models.candidate import Candidate
from iterlab.models.enums import CandidateStatus, RunStatus
from iterlab.models.experiment import Experiment, Run
from iterlab.models.lab import Lab
from iterlab.models.run_step import RunStep
from iterlab.schemas.agent import AgentOut
from iterlab.workflows.base import BenchmarkOutcome, CandidateInfo, StepContext, StepError
from iterlab.workflows.registry import get_step_handler

logger = logging.getLogger("iterlab.runs")


def _now() -> datetime:
    return datetime.now(UTC)


async def _upsert_candidate(
    session: AsyncSession, run: Run, existing: Candidate | None, info: CandidateInfo
) -> Candidate:
    cand = existing or Candidate(
        run_id=run.id, iteration=run.iteration, status=CandidateStatus.proposed
    )
    if existing is None:
        session.add(cand)
    if info.summary is not None:
        cand.summary = info.summary
    if info.commit_sha is not None:
        cand.commit_sha = info.commit_sha
    if info.branch is not None:
        cand.branch = info.branch
    if info.score is not None:
        cand.score = info.score
    if info.cost_usd is not None:
        cand.cost_usd = info.cost_usd
    if info.tokens is not None:
        cand.tokens = info.tokens
    merged = dict(cand.extra or {})
    if info.name:
        merged["name"] = info.name
    merged.update(info.extra or {})
    cand.extra = merged
    await session.flush()
    return cand


async def _record_benchmark(
    session: AsyncSession,
    lab_id: uuid.UUID,
    run: Run,
    candidate: Candidate | None,
    outcome: BenchmarkOutcome,
) -> None:
    if candidate is None:
        logger.warning("benchmark %s reported with no candidate — skipping", outcome.benchmark_slug)
        return
    bench = await session.scalar(
        select(Benchmark).where(
            Benchmark.lab_id == lab_id, Benchmark.slug == outcome.benchmark_slug
        )
    )
    if bench is None:
        logger.warning("no benchmark %r on lab — skipping result", outcome.benchmark_slug)
        return
    session.add(
        BenchmarkResult(
            benchmark_id=bench.id,
            candidate_id=candidate.id,
            run_id=run.id,
            score=outcome.score,
            passed=outcome.passed,
            details=outcome.details,
        )
    )
    primary = (run.context or {}).get("_primary_benchmark")
    if outcome.score is not None and outcome.benchmark_slug == primary:
        candidate.score = outcome.score
    await session.flush()


async def execute_run(session: AsyncSession, run_id: uuid.UUID) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise ValueError(f"run {run_id} not found")
    experiment = await session.get(Experiment, run.experiment_id)
    if experiment is None:
        raise ValueError(f"experiment {run.experiment_id} not found")
    lab = await session.get(Lab, experiment.lab_id)
    if lab is None:
        raise ValueError(f"lab {experiment.lab_id} not found")
    steps = (experiment.workflow or {}).get("steps", [])

    run.status = RunStatus.running
    run.started_at = _now()
    run.error = None
    await session.commit()
    logger.info("run %s: executing %d step(s)", run.id, len(steps))

    outputs: dict = dict(run.context or {})
    candidate: Candidate | None = await session.scalar(
        select(Candidate).where(Candidate.run_id == run.id)
    )

    lab_view = {
        "id": str(lab.id),
        "slug": lab.slug,
        "name": lab.name,
        "repo_url": lab.repo_url,
        "repo_branch": lab.repo_default_branch,
        "settings": lab.settings or {},
    }
    exp_view = {
        "id": str(experiment.id),
        "slug": experiment.slug,
        "name": experiment.name,
        "config": experiment.config or {},
    }
    agent_rows = await session.scalars(select(Agent))
    agents_view = {a.name: AgentOut.from_model(a).model_dump(mode="json") for a in agent_rows}

    for i, step_spec in enumerate(steps):
        handler_key = step_spec["handler"]
        rs = RunStep(
            run_id=run.id,
            position=i,
            handler=handler_key,
            name=step_spec.get("name"),
            config=step_spec.get("config", {}),
            status="running",
            started_at=_now(),
        )
        session.add(rs)
        await session.commit()

        ctx = StepContext(
            run_id=run.id,
            lab=lab_view,
            experiment=exp_view,
            step_config=step_spec.get("config", {}),
            outputs=outputs,
            agents=agents_view,
            logger=logging.getLogger(f"iterlab.step.{handler_key}"),
        )
        try:
            handler = get_step_handler(handler_key)
            result = await handler.run(ctx)
        except Exception as err:  # noqa: BLE001
            logger.exception("run %s step %d (%s) failed", run.id, i, handler_key)
            rs.status = "failed"
            rs.error = str(err)
            rs.output = getattr(err, "output", None) or None
            rs.finished_at = _now()
            sid = getattr(err, "agent_session_id", None) if isinstance(err, StepError) else None
            if sid:
                run.agent_session_id = sid
            run.status = RunStatus.failed
            run.error = f"step {i} ({handler_key}): {err}"
            run.finished_at = _now()
            if rs.output:
                outputs[handler_key] = rs.output
            run.context = outputs
            await session.commit()
            return run

        rs.status = "succeeded"
        rs.output = result.output
        rs.finished_at = _now()
        outputs[handler_key] = result.output
        outputs[str(i)] = result.output

        if result.agent_session_id:
            run.agent_session_id = result.agent_session_id
        if result.summary:
            run.summary = result.summary
        if result.candidate is not None:
            candidate = await _upsert_candidate(session, run, candidate, result.candidate)
        for outcome in result.benchmarks:
            await _record_benchmark(session, lab.id, run, candidate, outcome)

        run.context = outputs
        await session.commit()
        logger.info("run %s step %d (%s) ok", run.id, i, handler_key)

    run.status = RunStatus.succeeded
    run.finished_at = _now()
    run.context = outputs
    if candidate is not None:
        candidate.status = CandidateStatus.evaluated
    await session.commit()
    logger.info("run %s: done", run.id)
    return run
