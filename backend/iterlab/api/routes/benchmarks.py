from __future__ import annotations

import uuid

from fastapi import APIRouter

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.benchmarks import BenchmarkContext, Leaderboard, get_adapter
from iterlab.benchmarks.base import BenchmarkError
from iterlab.core.errors import APIError, NotFoundError
from iterlab.models.benchmark import Benchmark
from iterlab.schemas.benchmark import BenchmarkOut

router = APIRouter()


async def _get_benchmark(session: SessionDep, benchmark_id: uuid.UUID) -> Benchmark:
    bench = await session.get(Benchmark, benchmark_id)
    if bench is None:
        raise NotFoundError("benchmark not found")
    return bench


@router.get("/{benchmark_id}", response_model=BenchmarkOut, summary="Get a benchmark")
async def get_benchmark(
    benchmark_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Benchmark:
    return await _get_benchmark(session, benchmark_id)


@router.get(
    "/{benchmark_id}/leaderboard",
    response_model=Leaderboard,
    summary="Current standings for this benchmark",
)
async def benchmark_leaderboard(
    benchmark_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Leaderboard:
    bench = await _get_benchmark(session, benchmark_id)
    adapter = get_adapter(bench.adapter)
    ctx = BenchmarkContext(spec={**bench.spec, "_slug": bench.slug})
    try:
        return await adapter.leaderboard(ctx)
    except BenchmarkError as err:
        raise APIError(str(err), code="benchmark_unavailable") from err


@router.get("/{benchmark_id}/health", summary="Adapter reachability check")
async def benchmark_health(
    benchmark_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> dict:
    bench = await _get_benchmark(session, benchmark_id)
    adapter = get_adapter(bench.adapter)
    ctx = BenchmarkContext(spec={**bench.spec, "_slug": bench.slug})
    ok, detail = await adapter.health(ctx)
    return {"ok": ok, "detail": detail, "adapter": bench.adapter}
