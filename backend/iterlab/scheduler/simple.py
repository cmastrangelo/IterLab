from __future__ import annotations

from iterlab.scheduler.base import Assignment, Scheduler, TaskRequest, WorkerView


def _fits(req: dict, avail: dict) -> bool:
    return all(avail.get(k, 0) >= v for k, v in req.items())


def _labels_match(required: dict, have: dict) -> bool:
    return all(have.get(k) == v for k, v in required.items())


class GreedyScheduler(Scheduler):
    """Highest-priority task first; first worker that fits wins.

    Deducts the task's requirements from the worker's available resources so a
    single planning pass can place multiple tasks per worker.
    """

    def plan(
        self, tasks: list[TaskRequest], workers: list[WorkerView]
    ) -> list[Assignment]:
        avail = {
            w.worker_id: dict(w.resources_available)
            for w in workers
            if w.healthy
        }
        by_worker = {w.worker_id: w for w in workers}
        assignments: list[Assignment] = []

        for task in sorted(tasks, key=lambda t: (-t.priority, str(t.task_id))):
            for worker_id, remaining in avail.items():
                worker = by_worker[worker_id]
                if not _labels_match(task.labels, worker.labels):
                    continue
                if not _fits(task.requirements, remaining):
                    continue
                for k, v in task.requirements.items():
                    remaining[k] = remaining.get(k, 0) - v
                assignments.append(Assignment(task_id=task.task_id, worker_id=worker_id))
                break

        return assignments
