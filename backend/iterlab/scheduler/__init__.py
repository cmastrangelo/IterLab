from iterlab.scheduler.base import Scheduler, TaskRequest, WorkerView
from iterlab.scheduler.simple import GreedyScheduler

__all__ = ["Scheduler", "TaskRequest", "WorkerView", "GreedyScheduler", "get_scheduler"]


def get_scheduler() -> Scheduler:
    """Return the active scheduler.

    In-process greedy matcher today. Ray / ClearML / Kubernetes-Jobs backends
    implement :class:`Scheduler` later without changing callers.
    """
    return GreedyScheduler()
