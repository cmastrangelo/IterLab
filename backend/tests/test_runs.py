from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from iterlab.db.session import get_sessionmaker
from iterlab.labs.loader import sync_lab
from iterlab.labs.spec import BenchmarkSpec, LabSpec
from iterlab.models.experiment import Experiment
from iterlab.runs.executor import execute_run
from iterlab.workflows.base import (
    BenchmarkOutcome,
    CandidateInfo,
    StepContext,
    StepError,
    StepHandler,
    StepResult,
)
from iterlab.workflows.registry import register_step_handler
from iterlab.workflows.spec import StepSpec, WorkflowSpec


class _MakeSolution(StepHandler):
    key = "test_make_solution"

    async def run(self, ctx: StepContext) -> StepResult:
        return StepResult(
            output={"solution": "solution_99.py", "conversation_id": "conv-abc"},
            agent_session_id="conv-abc",
            summary="made solution_99.py",
            candidate=CandidateInfo(name="solution_99.py", summary="a change", cost_usd=0.5),
        )


class _Bench(StepHandler):
    key = "test_bench"

    async def run(self, ctx: StepContext) -> StepResult:
        sol = ctx.outputs["test_make_solution"]["solution"]
        return StepResult(
            output={"scored": sol, "win_pct": 61.0},
            benchmarks=[BenchmarkOutcome(benchmark_slug="board", score=61.0, passed=True)],
        )


class _Boom(StepHandler):
    key = "test_boom"

    async def run(self, ctx: StepContext) -> StepResult:
        raise StepError(
            "kaboom", output={"conversation_id": "conv-xyz"}, agent_session_id="conv-xyz"
        )


for h in (_MakeSolution, _Bench, _Boom):
    register_step_handler(h)


async def _lab_with_workflow(steps: list[StepSpec]) -> tuple[str, str]:
    spec = LabSpec(
        slug="run-lab",
        name="Run Lab",
        project_slug="run-proj",
        benchmarks=[BenchmarkSpec(slug="board", name="Board", adapter="sql_leaderboard")],
        workflow=WorkflowSpec(slug="iterate", name="Iterate", steps=steps),
    )
    async with get_sessionmaker()() as session:
        lab = await sync_lab(session, spec)
        exp = await session.scalar(select(Experiment).where(Experiment.lab_id == lab.id))
        await session.commit()
        assert exp is not None
        return str(lab.id), str(exp.id)


async def _auth(client: AsyncClient) -> dict:
    r = await client.post(
        "/auth/register",
        json={"email": "run@example.com", "password": "correct-horse-battery-staple"},
    )
    return {"authorization": f"Bearer {r.json()['tokens']['access_token']}"}


async def test_dispatch_and_execute_full_workflow(client: AsyncClient) -> None:
    headers = await _auth(client)
    _lab_id, exp_id = await _lab_with_workflow(
        [StepSpec(handler="test_make_solution"), StepSpec(handler="test_bench")]
    )

    run = (await client.post(f"/experiments/{exp_id}/runs", headers=headers)).json()
    assert run["status"] == "pending"

    async with get_sessionmaker()() as session:
        await execute_run(session, uuid.UUID(run["id"]))

    detail = (await client.get(f"/runs/{run['id']}", headers=headers)).json()
    assert detail["status"] == "succeeded"
    assert detail["agent_session_id"] == "conv-abc"
    assert [s["handler"] for s in detail["steps"]] == ["test_make_solution", "test_bench"]
    assert all(s["status"] == "succeeded" for s in detail["steps"])
    assert detail["candidate"]["extra"]["name"] == "solution_99.py"
    assert detail["benchmark_results"][0]["score"] == 61.0
    assert detail["benchmark_results"][0]["passed"] is True


async def test_failing_step_records_session_id_and_marks_failed(client: AsyncClient) -> None:
    headers = await _auth(client)
    _lab_id, exp_id = await _lab_with_workflow([StepSpec(handler="test_boom")])
    run = (await client.post(f"/experiments/{exp_id}/runs", headers=headers)).json()

    async with get_sessionmaker()() as session:
        await execute_run(session, uuid.UUID(run["id"]))

    detail = (await client.get(f"/runs/{run['id']}", headers=headers)).json()
    assert detail["status"] == "failed"
    assert "kaboom" in detail["error"]
    assert detail["agent_session_id"] == "conv-xyz"
    assert detail["steps"][0]["status"] == "failed"


async def test_run_requires_workflow(client: AsyncClient) -> None:
    headers = await _auth(client)
    async with get_sessionmaker()() as session:
        spec = LabSpec(slug="empty-lab", name="Empty", project_slug="empty")
        lab = await sync_lab(session, spec)
        exp = Experiment(lab_id=lab.id, slug="x", name="x", workflow={})
        session.add(exp)
        await session.commit()
        exp_id = str(exp.id)

    resp = await client.post(f"/experiments/{exp_id}/runs", headers=headers)
    assert resp.status_code == 400
