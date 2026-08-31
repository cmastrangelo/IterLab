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
