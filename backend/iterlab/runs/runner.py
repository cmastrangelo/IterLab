"""Local run executor.

A minimal worker for single-host deployments: it claims pending runs straight
from the database and executes their workflows in-process (loading the same
instance adapter plugins the API does). The HTTP worker protocol
(``iterlab.workers``) is the path for distributed / untrusted workers.

    python -m iterlab.runs.runner --once      # execute the next pending run, exit
    python -m iterlab.runs.runner --watch     # keep polling

Run it on a host that has whatever the workflow's step handlers need (e.g. the
``claude`` CLI and the target repo checkout).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from sqlalchemy import select, update

from iterlab.db.session import dispose_engine, get_sessionmaker
from iterlab.instance import initialize_instance
from iterlab.logging_config import configure_logging
from iterlab.models.experiment import Run
from iterlab.runs.executor import execute_run

logger = logging.getLogger("iterlab.runner")


async def _claim_next_run() -> uuid.UUID | None:
    """Atomically move one pending run to 'scheduled' and return its id."""
    next_pending = (
        select(Run.id).where(Run.status == "pending").order_by(Run.created_at).limit(1)
    ).scalar_subquery()
    async with get_sessionmaker()() as session:
        claimed = await session.scalar(
            update(Run)
            .where(Run.id.in_(next_pending))
            .values(status="scheduled")
            .returning(Run.id)
        )
        await session.commit()
        return claimed


async def _run_one() -> bool:
    run_id = await _claim_next_run()
    if run_id is None:
        return False
    logger.info("claimed run %s", run_id)
    async with get_sessionmaker()() as session:
        try:
            await execute_run(session, run_id)
        except Exception:  # noqa: BLE001
            logger.exception("run %s crashed", run_id)
    return True


async def _main(watch: bool, interval: float) -> None:
    configure_logging("INFO", json=False)
    initialize_instance()
    import iterlab.benchmarks  # noqa: F401  (register adapters + step handlers)

    try:
        while True:
            did = await _run_one()
            if not watch:
                if not did:
                    logger.info("no pending runs")
                break
            if not did:
                await asyncio.sleep(interval)
    finally:
        await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true", help="run the next pending run, then exit")
    group.add_argument("--watch", action="store_true", help="keep polling for runs")
    parser.add_argument("--interval", type=float, default=5.0, help="poll interval for --watch")
    args = parser.parse_args()
    asyncio.run(_main(watch=args.watch, interval=args.interval))


if __name__ == "__main__":
    main()
