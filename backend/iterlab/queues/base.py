"""Coordination primitives.

``Queue`` and ``KeyValue`` describe the *ephemeral* side of IterLab. PostgreSQL
remains the source of truth; anything here can be rebuilt from it. Redis backs
both today; NATS/SQS/Kafka can implement ``Queue`` later.
"""

from __future__ import annotations

import abc


class Queue(abc.ABC):
    @abc.abstractmethod
    async def push(self, topic: str, message: str, *, priority: int = 100) -> None: ...

    @abc.abstractmethod
    async def pop(self, topic: str, *, timeout: float = 0.0) -> str | None: ...

    @abc.abstractmethod
    async def size(self, topic: str) -> int: ...


class KeyValue(abc.ABC):
    @abc.abstractmethod
    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None: ...

    @abc.abstractmethod
    async def get(self, key: str) -> str | None: ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    async def acquire_lock(self, key: str, *, ttl: int = 30) -> str | None:
        """Return a lock token on success, else None."""

    @abc.abstractmethod
    async def release_lock(self, key: str, token: str) -> None: ...
