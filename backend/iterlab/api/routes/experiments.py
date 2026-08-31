from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import APIError, NotFoundError
from iterlab.models.benchmark import BenchmarkResult
from iterlab.models.candidate import Candidate
from iterlab.models.enums import RunStatus
from iterlab.models.experiment import Experiment, Run
from iterlab.models.run_step import RunStep
from iterlab.schemas.experiment import (
    BenchmarkResultOut,
    CandidateOut,
    ExperimentOut,
    RunDetailOut,
    RunOut,
    RunStepOut,
)

router = APIRouter()


# --- experiments (under a lab) -----------------------------------------
lab_experiments = APIRouter()


@lab_experiments.get(
    "/{lab_id}/experiments", response_model=list[ExperimentOut], summary="List a lab's experiments"
)
async def list_experiments(
    lab_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[Experiment]:
    return list(
        await session.scalars(
            select(Experiment).where(Experiment.lab_id == lab_id).order_by(Experiment.created_at)
        )
    )


# --- experiments / runs ------------------------------------------------
async def _get_experiment(session: SessionDep, experiment_id: uuid.UUID) -> Experiment:
    exp = await session.get(Experiment, experiment_id)
    if exp is None:
        raise NotFoundError("experiment not found")
    return exp


@router.get("/{experiment_id}", response_model=ExperimentOut, summary="Get an experiment")
async def get_experiment(
    experiment_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Experiment:
    return await _get_experiment(session, experiment_id)


@router.get(
    "/{experiment_id}/runs", response_model=list[RunOut], summary="List an experiment's runs"
)
async def list_runs(
    experiment_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[Run]:
    return list(
        await session.scalars(
            select(Run).where(Run.experiment_id == experiment_id).order_by(Run.created_at.desc())
        )
    )


@router.post(
    "/{experiment_id}/runs",
    response_model=RunOut,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a run of this experiment (a local runner executes it)",
)
async def create_run(
    experiment_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Run:
    exp = await _get_experiment(session, experiment_id)
    if not (exp.workflow or {}).get("steps"):
        raise APIError("experiment has no workflow steps to run", code="no_workflow")

    last = await session.scalar(
        select(Run).where(Run.experiment_id == exp.id).order_by(Run.iteration.desc()).limit(1)
    )
    run = Run(
        experiment_id=exp.id,
        status="pending",
        iteration=(last.iteration + 1) if last else 1,
        context={},
    )
    session.add(run)
    await session.flush()
    return run


# --- runs -------------------------------------------------------------
runs = APIRouter()


@runs.post(
    "/{run_id}/retry",
    response_model=RunOut,
    summary="Re-queue a failed run (resumes from the first unfinished step)",
)
async def retry_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Run:
    run = await session.get(Run, run_id)
    if run is None:
        raise NotFoundError("run not found")
    if str(run.status) not in {"failed", "cancelled", "lost"}:
        raise APIError(f"run is {run.status}, not retryable", code="not_retryable")
    run.status = RunStatus.pending
    run.error = None
    run.finished_at = None
    await session.flush()
    return run


@runs.get("/{run_id}", response_model=RunDetailOut, summary="Run detail with steps + results")
async def get_run(run_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> RunDetailOut:
    run = await session.get(Run, run_id)
    if run is None:
        raise NotFoundError("run not found")
    steps = await session.scalars(
        select(RunStep).where(RunStep.run_id == run.id).order_by(RunStep.position)
    )
    candidate = await session.scalar(select(Candidate).where(Candidate.run_id == run.id))
    results = await session.scalars(
        select(BenchmarkResult).where(BenchmarkResult.run_id == run.id)
    )

    detail = RunDetailOut.model_validate(run)
    detail.steps = [RunStepOut.model_validate(s) for s in steps]
    detail.candidate = CandidateOut.model_validate(candidate) if candidate else None
    detail.benchmark_results = [BenchmarkResultOut.model_validate(r) for r in results]
    detail.context = run.context or {}
    return detail
