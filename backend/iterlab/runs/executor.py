"""Execute a run.

A run's workflow is an ordered list of steps, optionally repeated
``workflow.iterations`` times. Each iteration produces its own candidate; the
run's context (e.g. an agent conversation id) carries across iterations so a
later iteration can build on the earlier ones.

The executor is resumable: a re-dispatched run skips ``(iteration, position)``
pairs that already succeeded and replays their outputs.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.models.agent import Agent
from iterlab.models.benchmark import Benchmark, BenchmarkResult
from iterlab.models.candidate import Candidate
from iterlab.models.enums import CandidateStatus, RunStatus
from iterlab.models.experiment import Experiment, Run
from iterlab.models.lab import Lab
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.schemas.agent import AgentOut
from iterlab.workflows.base import (
    BenchmarkOutcome,
    CandidateInfo,
    PromptRef,
    StepContext,
    StepError,
)
from iterlab.workflows.registry import get_step_handler

logger = logging.getLogger("iterlab.runs")


def _now() -> datetime:
    return datetime.now(UTC)


def _apply_candidate(cand: Candidate, info: CandidateInfo) -> None:
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


async def _candidate_for(session: AsyncSession, run: Run, iteration: int) -> Candidate:
    cand = await session.scalar(
        select(Candidate).where(
            Candidate.run_id == run.id, Candidate.iteration == iteration
        )
    )
    if cand is None:
        cand = Candidate(run_id=run.id, iteration=iteration, status=CandidateStatus.proposed)
        session.add(cand)
        await session.flush()
    return cand


async def _version_prompt(session: AsyncSession, lab_id: uuid.UUID, ref: PromptRef) -> Prompt:
    digest = hashlib.sha256(ref.template.encode()).hexdigest()
    existing = await session.scalar(
        select(Prompt).where(
            Prompt.lab_id == lab_id, Prompt.slug == ref.slug, Prompt.digest == digest
        )
    )
    if existing is not None:
        return existing
    max_v = await session.scalar(
        select(func.max(Prompt.version)).where(
            Prompt.lab_id == lab_id, Prompt.slug == ref.slug
        )
    )
    prompt = Prompt(
        lab_id=lab_id,
        slug=ref.slug,
        version=0 if max_v is None else max_v + 1,
        text=ref.template,
        digest=digest,
    )
    session.add(prompt)
    await session.flush()
    logger.info("recorded prompt %s v%d for lab %s", ref.slug, prompt.version, lab_id)
    return prompt


async def _record_benchmark(
    session: AsyncSession,
    lab_id: uuid.UUID,
    run: Run,
    candidate: Candidate,
    outcome: BenchmarkOutcome,
) -> None:
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

    workflow = experiment.workflow or {}
    steps: list[dict] = [dict(s) for s in workflow.get("steps", [])]
    ctx_state = dict(run.context or {})
    iterations = int(ctx_state.get("iterations") or workflow.get("iterations", 1))

    # per-run agent override: applied to any step whose config names an agent
    agent_override = ctx_state.get("agent_override")
    if agent_override:
        for step in steps:
            cfg = dict(step.get("config") or {})
            if cfg.get("agent"):
                cfg["agent"] = agent_override
                step["config"] = cfg

    run.status = RunStatus.running
    run.started_at = _now()
    run.error = None
    await session.commit()
    logger.info("run %s: %d step(s) x %d iteration(s)", run.id, len(steps), iterations)

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
        "workflow": workflow,
        "iterations": iterations,
    }
    agent_rows = await session.scalars(select(Agent))
    agents_view = {a.name: AgentOut.from_model(a).model_dump(mode="json") for a in agent_rows}

    # resume: replay outputs of already-succeeded (iteration, position) pairs
    prior = list(
        await session.scalars(
            select(RunStep).where(RunStep.run_id == run.id)
        )
    )
    done: set[tuple[int, int]] = set()
    history: list[dict] = [{} for _ in range(iterations)]
    for ps in prior:
        if ps.status == "succeeded" and ps.iteration < iterations:
            done.add((ps.iteration, ps.position))
            history[ps.iteration][ps.handler] = ps.output or {}
        else:
            await session.delete(ps)
    await session.commit()

    for it in range(iterations):
        iter_outputs: dict = dict(history[it])
        for pos, step_spec in enumerate(steps):
            handler_key = step_spec["handler"]
            if (it, pos) in done:
                logger.info("run %s [%d.%d %s]: done, skipping", run.id, it, pos, handler_key)
                continue

            rs = RunStep(
                run_id=run.id,
                iteration=it,
                position=pos,
                handler=handler_key,
                name=step_spec.get("name"),
                config=step_spec.get("config", {}),
                status="running",
                started_at=_now(),
            )
            session.add(rs)
            await session.commit()

            async def _checkpoint(partial: dict, _rs: RunStep = rs) -> None:
                _rs.output = {**(_rs.output or {}), **partial}
                sid = partial.get("agent_session_id") or partial.get("conversation_id")
                if sid:
                    run.agent_session_id = sid
                await session.commit()

            ctx = StepContext(
                run_id=run.id,
                lab=lab_view,
                experiment=exp_view,
                step_config=step_spec.get("config", {}),
                iteration=it,
                outputs=iter_outputs,
                history=history[:it],
                agent_session_id=run.agent_session_id,
                agents=agents_view,
                logger=logging.getLogger(f"iterlab.step.{handler_key}"),
                checkpoint=_checkpoint,
            )
            try:
                result = await get_step_handler(handler_key).run(ctx)
            except Exception as err:  # noqa: BLE001
                logger.exception("run %s [%d.%d %s] failed", run.id, it, pos, handler_key)
                rs.status = "failed"
                rs.error = str(err)
                rs.output = getattr(err, "output", None) or None
                rs.finished_at = _now()
                sid = getattr(err, "agent_session_id", None) if isinstance(err, StepError) else None
                if sid:
                    run.agent_session_id = sid
                run.status = RunStatus.failed
                run.error = f"iteration {it} step {pos} ({handler_key}): {err}"
                run.finished_at = _now()
                run.context = {**ctx_state, "iterations": iterations}
                await session.commit()
                return run

            rs.status = "succeeded"
            rs.output = result.output
            rs.finished_at = _now()

            if result.prompt is not None:
                prompt = await _version_prompt(session, lab.id, result.prompt)
                rs.prompt_id = prompt.id
                rs.output = {
                    **result.output,
                    "prompt_id": str(prompt.id),
                    "prompt_slug": prompt.slug,
                    "prompt_version": prompt.version,
                }
            iter_outputs[handler_key] = rs.output

            if result.agent_session_id:
                run.agent_session_id = result.agent_session_id
            if result.summary:
                run.summary = result.summary
            if result.candidate is not None or result.benchmarks:
                cand = await _candidate_for(session, run, it)
                if result.candidate is not None:
                    _apply_candidate(cand, result.candidate)
                if result.prompt is not None:
                    pv = rs.output["prompt_version"]
                    cand.extra = {**(cand.extra or {}), "prompt_version": pv}
                for outcome in result.benchmarks:
                    await _record_benchmark(session, lab.id, run, cand, outcome)

            await session.commit()
            logger.info("run %s [%d.%d %s] ok", run.id, it, pos, handler_key)

        history[it] = iter_outputs
        done_cand = await session.scalar(
            select(Candidate).where(Candidate.run_id == run.id, Candidate.iteration == it)
        )
        if done_cand is not None:
            done_cand.status = CandidateStatus.evaluated
        run.context = {
            **ctx_state,
            "iterations": iterations,
            "iterations_done": it + 1,
            "agent_session_id": run.agent_session_id,
        }
        await session.commit()

    run.status = RunStatus.succeeded
    run.finished_at = _now()
    await session.commit()
    logger.info("run %s: done (%d candidate iteration(s))", run.id, iterations)
    return run
