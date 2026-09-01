from __future__ import annotations

import pytest
from httpx import AsyncClient

from iterlab.benchmarks.base import (
    BenchmarkAdapter,
    Leaderboard,
    LeaderboardColumn,
    LeaderboardRow,
)
from iterlab.benchmarks.registry import register_adapter
from iterlab.db.session import get_sessionmaker
from iterlab.labs.loader import sync_lab
from iterlab.labs.spec import BenchmarkSpec, LabSpec


class _StubAdapter(BenchmarkAdapter):
    key = "stub_leaderboard"
    summary = "test adapter"

    async def leaderboard(self, ctx) -> Leaderboard:
        top = ctx.spec.get("rows", 3)
        return Leaderboard(
            benchmark_slug=ctx.spec.get("_slug", "x"),
            title="Stub",
            columns=[LeaderboardColumn(key="score", label="Score", kind="number", primary=True)],
            rows=[
                LeaderboardRow(
                    rank=i, entrant=f"entry_{i}", score=100 - i, values={"score": 100 - i}
                )
                for i in range(1, top + 1)
            ],
        )


register_adapter(_StubAdapter)


@pytest.fixture
async def _instance_lab():
    spec = LabSpec(
        slug="test-lab",
        name="Test Lab",
        project_slug="test-proj",
        benchmarks=[
            BenchmarkSpec(
                slug="board",
                name="Board",
                adapter="stub_leaderboard",
                primary_metric="score",
                spec={"rows": 4},
            )
        ],
    )
    async with get_sessionmaker()() as session:
        lab = await sync_lab(session, spec)
        await session.commit()
        return str(lab.id)


async def _auth(client: AsyncClient) -> dict:
    r = await client.post(
        "/auth/register",
        json={"email": "lab@example.com", "password": "correct-horse-battery-staple"},
    )
    return {"authorization": f"Bearer {r.json()['tokens']['access_token']}"}


async def test_instance_lab_is_listed_and_read_only_flagged(client: AsyncClient, _instance_lab):
    headers = await _auth(client)
    labs = (await client.get("/labs", headers=headers)).json()
    assert any(x["slug"] == "test-lab" and x["source"] == "instance" for x in labs)

    detail = (await client.get(f"/labs/{_instance_lab}", headers=headers)).json()
    assert [b["slug"] for b in detail["benchmarks"]] == ["board"]
    assert detail["benchmarks"][0]["managed"] is True
    assert detail["benchmarks"][0]["adapter"] == "stub_leaderboard"


async def test_benchmark_leaderboard_runs_adapter(client: AsyncClient, _instance_lab):
    headers = await _auth(client)
    detail = (await client.get(f"/labs/{_instance_lab}", headers=headers)).json()
    bid = detail["benchmarks"][0]["id"]

    board = (await client.get(f"/benchmarks/{bid}/leaderboard", headers=headers)).json()
    assert board["title"] == "Stub"
    assert len(board["rows"]) == 4
    assert board["rows"][0] == {
        "rank": 1,
        "entrant": "entry_1",
        "score": 99.0,
        "is_baseline": False,
        "is_candidate": False,
        "values": {"score": 99},
    }

    health = (await client.get(f"/benchmarks/{bid}/health", headers=headers)).json()
    assert health["ok"] is True


async def test_candidate_labels_benchmark_ranks_by_label(client: AsyncClient):
    from iterlab.models.candidate import Candidate
    from iterlab.models.experiment import Experiment, Run

    spec = LabSpec(
        slug="cl-lab",
        name="CL Lab",
        project_slug="cl-proj",
        benchmarks=[
            BenchmarkSpec(
                slug="league",
                name="League",
                adapter="candidate_labels",
                primary_metric="placement",
                higher_is_better=False,
                spec={
                    "label_key": "placement",
                    "sort": "tiered",
                    "tiers": ["Legend", "Gold", "Silver"],
                    "within_tier_order": "asc",
                    "extra_entrants": [
                        {"entrant": "baseline.py", "value": "Gold 500", "baseline": True}
                    ],
                },
            )
        ],
    )
    async with get_sessionmaker()() as session:
        lab = await sync_lab(session, spec)
        exp = Experiment(lab_id=lab.id, slug="e", name="e", workflow={})
        session.add(exp)
        await session.flush()
        run = Run(experiment_id=exp.id, status="succeeded", iteration=1)
        session.add(run)
        await session.flush()
        session.add_all(
            [
                Candidate(
                    run_id=run.id, iteration=0, score=61.0,
                    extra={"name": "sol_a.py"}, labels={"placement": "Gold 90"},
                ),
                Candidate(
                    run_id=run.id, iteration=1, score=66.0,
                    extra={"name": "sol_b.py"}, labels={"placement": "Gold 12"},
                ),
                Candidate(
                    run_id=run.id, iteration=2, score=59.0,
                    extra={"name": "sol_c.py"}, labels={"placement": "Silver 3"},
                ),
                Candidate(  # no label -> excluded
                    run_id=run.id, iteration=3, score=70.0, extra={"name": "sol_d.py"},
                ),
            ]
        )
        await session.commit()
        lab_id = str(lab.id)

    headers = await _auth(client)
    detail = (await client.get(f"/labs/{lab_id}", headers=headers)).json()
    bid = detail["benchmarks"][0]["id"]
    board = (await client.get(f"/benchmarks/{bid}/leaderboard", headers=headers)).json()

    # Gold beats Silver; within Gold lower number is better; baseline.py (Gold 500) last
    assert [r["entrant"] for r in board["rows"]] == [
        "sol_b.py", "sol_a.py", "baseline.py", "sol_c.py",
    ]
    assert [r["values"]["value"] for r in board["rows"]] == [
        "Gold 12", "Gold 90", "Gold 500", "Silver 3",
    ]
    assert board["rows"][0]["values"]["local"] == 66.0
    assert board["rows"][2]["is_baseline"] is True

    health = (await client.get(f"/benchmarks/{bid}/health", headers=headers)).json()
    assert health["ok"] is True and "4 labelled" in health["detail"]


async def test_resync_updates_and_prunes_benchmarks(client: AsyncClient, _instance_lab):
    headers = await _auth(client)
    spec = LabSpec(
        slug="test-lab",
        name="Test Lab Renamed",
        project_slug="test-proj",
        benchmarks=[],  # drop the managed benchmark
    )
    async with get_sessionmaker()() as session:
        await sync_lab(session, spec)
        await session.commit()

    detail = (await client.get(f"/labs/{_instance_lab}", headers=headers)).json()
    assert detail["name"] == "Test Lab Renamed"
    assert detail["benchmarks"] == []
