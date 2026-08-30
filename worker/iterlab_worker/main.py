from __future__ import annotations

import logging
import signal
import time

from iterlab_worker.client import ControllerClient, WorkerIdentity
from iterlab_worker.config import WorkerSettings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("iterlab-worker")

_running = True


def _stop(*_: object) -> None:
    global _running
    _running = False
    logger.info("shutdown requested")


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    settings = WorkerSettings()
    client = ControllerClient(settings)

    identity = WorkerIdentity.load(settings.state_file)
    if identity is None:
        logger.info("registering worker %r with %s", settings.name, settings.base_url)
        identity = client.register()
        identity.save(settings.state_file)
        logger.info("registered as worker %s", identity.worker_id)
    else:
        logger.info("resuming as worker %s", identity.worker_id)

    interval = 15
    try:
        while _running:
            try:
                hb = client.heartbeat(identity)
                interval = int(hb.get("heartbeat_interval_s", interval)) if hb else interval

                task = client.pull_task(identity)
                if task:
                    logger.info("received task %s (%s) — execution not yet implemented",
                                task.get("task_id"), task.get("kind"))
            except Exception:  # noqa: BLE001 - keep the loop alive
                logger.exception("heartbeat/poll cycle failed")

            for _ in range(interval):
                if not _running:
                    break
                time.sleep(1)
    finally:
        client.close()
        logger.info("worker stopped")


if __name__ == "__main__":
    main()
