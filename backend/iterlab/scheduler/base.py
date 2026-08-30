"""Scheduler abstraction: match pending tasks to capable workers.

The scheduler is pure decision logic — it does not touch the database or Redis
directly. The control plane feeds it the current pending tasks and known
workers, and applies the returned assignments.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field


@dataclass(slots=True)
class TaskRequest:
    task_id: uuid.UUID
    priority: int = 100
    requirements: dict = field(default_factory=dict)  # {"cpu": 2, "gpu": 1, "vram_mb": 8000}
    labels: dict = field(default_factory=dict)         # required worker labels


@dataclass(slots=True)
class WorkerView:
    worker_id: uuid.UUID
    resources_available: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)
    healthy: bool = True


@dataclass(slots=True)
class Assignment:
    task_id: uuid.UUID
    worker_id: uuid.UUID


class Scheduler(abc.ABC):
    @abc.abstractmethod
    def plan(
        self, tasks: list[TaskRequest], workers: list[WorkerView]
    ) -> list[Assignment]: ...
