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
    PromptRef,
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


class _IterAgent(StepHandler):
    """Records its iteration index and what it saw from the prior iteration."""

    key = "test_iter_agent"

    async def run(self, ctx: StepContext) -> StepResult:
        prior_score = None
        if ctx.history:
            prior_score = ctx.history[-1].get("test_iter_bench", {}).get("score")
        sid = ctx.outputs.get("_sid") or f"conv-{ctx.iteration if ctx.iteration == 0 else 'kept'}"
        return StepResult(
            output={"iteration": ctx.iteration, "saw_prior_score": prior_score, "_sid": sid},
            agent_session_id="conv-fixed" if ctx.iteration == 0 else None,
            candidate=CandidateInfo(name=f"sol_{ctx.iteration}.py"),
        )


class _IterBench(StepHandler):
    key = "test_iter_bench"

    async def run(self, ctx: StepContext) -> StepResult:
        sol = ctx.outputs["test_iter_agent"]["_sid"]  # any value from this iteration
        score = 50.0 + ctx.iteration * 3
        return StepResult(
            output={"score": score, "for": sol},
            candidate=CandidateInfo(name=f"sol_{ctx.iteration}.py", score=score),
            benchmarks=[BenchmarkOutcome(benchmark_slug="board", score=score)],
        )


class _PromptAgent(StepHandler):
    """Emits a versioned prompt whose template is controlled by step config."""

    key = "test_prompt_agent"

    async def run(self, ctx: StepContext) -> StepResult:
        template = ctx.step_config.get("template", "base template {x}")
        slug = ctx.step_config.get("slug", "initial")
        return StepResult(
            output={"iteration": ctx.iteration},
            candidate=CandidateInfo(name=f"sol_{ctx.iteration}.py", score=60.0),
            prompt=PromptRef(slug=slug, template=template, rendered=template),
        )


class _CostAgent(StepHandler):
    """Agent step that reports a fixed USD cost per iteration."""

    key = "test_cost_agent"

    async def run(self, ctx: StepContext) -> StepResult:
        per = float(ctx.step_config.get("cost", 0.4))
        return StepResult(
            output={"iteration": ctx.iteration, "cost_usd": per},
            candidate=CandidateInfo(name=f"sol_{ctx.iteration}.py", cost_usd=per),
        )


class _Boom(StepHandler):
    key = "test_boom"

    async def run(self, ctx: StepContext) -> StepResult:
        raise StepError(
            "kaboom", output={"conversation_id": "conv-xyz"}, agent_session_id="conv-xyz"
        )


for h in (_MakeSolution, _Bench, _Boom, _IterAgent, _IterBench, _PromptAgent, _CostAgent):
    register_step_handler(h)


async def _lab_with_workflow(
    steps: list[StepSpec], iterations: int = 1, slug: str = "run-lab"
) -> tuple[str, str]:
    spec = LabSpec(
        slug=slug,
        name="Run Lab",
        project_slug="run-proj",
        benchmarks=[BenchmarkSpec(slug="board", name="Board", adapter="sql_leaderboard")],
        workflow=WorkflowSpec(
            slug="iterate", name="Iterate", iterations=iterations, steps=steps
        ),
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
    assert detail["candidates"][0]["extra"]["name"] == "solution_99.py"
    assert detail["candidates"][0]["status"] == "evaluated"
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


async def test_iteration_loop_produces_a_candidate_per_iteration(client: AsyncClient) -> None:
    headers = await _auth(client)
    _lab_id, exp_id = await _lab_with_workflow(
        [StepSpec(handler="test_iter_agent"), StepSpec(handler="test_iter_bench")],
        iterations=3,
    )
    run = (await client.post(f"/experiments/{exp_id}/runs", headers=headers)).json()
    async with get_sessionmaker()() as session:
        await execute_run(session, uuid.UUID(run["id"]))

    detail = (await client.get(f"/runs/{run['id']}", headers=headers)).json()
    assert detail["status"] == "succeeded"
    # 3 iterations x 2 steps
    assert [(s["iteration"], s["handler"]) for s in detail["steps"]] == [
        (0, "test_iter_agent"), (0, "test_iter_bench"),
        (1, "test_iter_agent"), (1, "test_iter_bench"),
        (2, "test_iter_agent"), (2, "test_iter_bench"),
    ]
    # one candidate per iteration, each scored
    cands = detail["candidates"]
    assert [c["iteration"] for c in cands] == [0, 1, 2]
    assert [c["score"] for c in cands] == [50.0, 53.0, 56.0]
    assert [c["extra"]["name"] for c in cands] == ["sol_0.py", "sol_1.py", "sol_2.py"]
    # conversation id set in iteration 0 carries through
    assert detail["agent_session_id"] == "conv-fixed"
    # iteration 2's agent saw iteration 1's benchmark score
    iter2_agent = next(
        s
        for s in detail["steps"]
        if s["iteration"] == 2 and s["handler"] == "test_iter_agent"
    )
    assert iter2_agent["output"]["saw_prior_score"] == 53.0


async def test_prompt_versions_are_recorded_and_deduped(client: AsyncClient) -> None:
    headers = await _auth(client)

    async def _run(exp_id: str) -> str:
        run = (await client.post(f"/experiments/{exp_id}/runs", headers=headers)).json()
        async with get_sessionmaker()() as session:
            await execute_run(session, uuid.UUID(run["id"]))
        return run["id"]

    # lab A: two runs, same template -> a single v0
    lab_a, exp_a = await _lab_with_workflow(
        [StepSpec(handler="test_prompt_agent", config={"template": "climb the ladder {x}"})],
        slug="prompt-lab-a",
    )
    await _run(exp_a)
    await _run(exp_a)
    rows = (await client.get(f"/labs/{lab_a}/prompts", headers=headers)).json()
    assert [(r["slug"], r["version"]) for r in rows] == [("initial", 0)]
    assert rows[0]["uses"] == 2
    assert rows[0]["scored"] == 2
    assert rows[0]["best_score"] == 60.0

    # a different lab keeps its own prompt version space
    lab_b, exp_b = await _lab_with_workflow(
        [StepSpec(handler="test_prompt_agent", config={"template": "v-one {x}"})],
        slug="prompt-lab-b",
    )
    rows_b0 = (await client.get(f"/labs/{lab_b}/prompts", headers=headers)).json()
    assert rows_b0 == []
    await _run(exp_b)
    rows_b = (await client.get(f"/labs/{lab_b}/prompts", headers=headers)).json()
    assert [(r["slug"], r["version"]) for r in rows_b] == [("initial", 0)]

    # candidate carries the prompt_version it was produced under
    run_id = (await client.get(f"/experiments/{exp_a}/runs", headers=headers)).json()
    detail = (await client.get(f"/runs/{run_id[0]['id']}", headers=headers)).json()
    assert detail["candidates"][0]["extra"]["prompt_version"] == 0


async def test_cost_cap_pauses_run_and_resume_continues(client: AsyncClient) -> None:
    headers = await _auth(client)
    _lab_id, exp_id = await _lab_with_workflow(
        [StepSpec(handler="test_cost_agent", config={"cost": 0.4})],
        iterations=4,
        slug="cost-lab",
    )
    run = (
        await client.post(
            f"/experiments/{exp_id}/runs",
            headers=headers,
            json={"iterations": 4, "cost_budget_usd": 1.0},
        )
    ).json()

    async with get_sessionmaker()() as session:
        await execute_run(session, uuid.UUID(run["id"]))

    detail = (await client.get(f"/runs/{run['id']}", headers=headers)).json()
    # 0.4 * 3 = 1.2 >= 1.0 cap -> pauses before iteration 3's step
    assert detail["status"] == "paused"
    assert detail["context"]["spent_usd"] == 1.2
    assert detail["context"]["iterations_done"] == 3
    assert detail["context"]["cost_budget_usd"] == 1.0
    assert "cost cap" in detail["context"]["paused_reason"]
    assert len(detail["candidates"]) == 3

    # resume: default +$2 ceiling -> 3.0, run finishes
    resumed = await client.post(f"/runs/{run['id']}/resume", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["status"] == "pending"

    async with get_sessionmaker()() as session:
        await execute_run(session, uuid.UUID(run["id"]))

    detail = (await client.get(f"/runs/{run['id']}", headers=headers)).json()
    assert detail["status"] == "succeeded"
    assert detail["context"]["spent_usd"] == 1.6
    assert detail["context"]["cost_budget_usd"] == 3.0
    assert len(detail["candidates"]) == 4


async def test_resume_rejects_non_paused_run(client: AsyncClient) -> None:
    headers = await _auth(client)
    _lab_id, exp_id = await _lab_with_workflow(
        [StepSpec(handler="test_cost_agent")], slug="cost-lab-2"
    )
    run = (await client.post(f"/experiments/{exp_id}/runs", headers=headers)).json()
    resp = await client.post(f"/runs/{run['id']}/resume", headers=headers)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "not_paused"


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
