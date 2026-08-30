from __future__ import annotations

import secrets

import redis.asyncio as redis

from iterlab.queues.base import KeyValue, Queue

_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class RedisBackend(Queue, KeyValue):
    """Redis-backed Queue + KeyValue.

    Queues use a per-priority sorted set (score = priority, then FIFO by a
    monotonic suffix). Good enough for the skeleton; swap for Streams when
    consumer groups / acks are needed.
    """

    def __init__(self, client: redis.Redis):
        self._r = client
        self._seq = 0

    @classmethod
    def from_url(cls, url: str) -> RedisBackend:
        return cls(redis.from_url(url, decode_responses=True))

    async def close(self) -> None:
        await self._r.aclose()

    async def ping(self) -> bool:
        return bool(await self._r.ping())

    # -- Queue ---------------------------------------------------------
    def _qkey(self, topic: str) -> str:
        return f"iterlab:queue:{topic}"

    async def push(self, topic: str, message: str, *, priority: int = 100) -> None:
        self._seq += 1
        score = priority * 1e12 + self._seq
        await self._r.zadd(self._qkey(topic), {message: score})

    async def pop(self, topic: str, *, timeout: float = 0.0) -> str | None:
        key = self._qkey(topic)
        if timeout > 0:
            item = await self._r.bzpopmin(key, timeout=timeout)
            return str(item[1]) if item else None
        popped = await self._r.zpopmin(key, count=1)
        return str(popped[0][0]) if popped else None

    async def size(self, topic: str) -> int:
        return int(await self._r.zcard(self._qkey(topic)))

    # -- KeyValue -----------------------------------------------------
    def _kvkey(self, key: str) -> str:
        return f"iterlab:kv:{key}"

    async def set(self, key: str, value: str, *, ttl: int | None = None) -> None:
        await self._r.set(self._kvkey(key), value, ex=ttl)

    async def get(self, key: str) -> str | None:
        value = await self._r.get(self._kvkey(key))
        return None if value is None else str(value)

    async def delete(self, key: str) -> None:
        await self._r.delete(self._kvkey(key))

    # -- locks ------------------------------------------------------
    def _lockkey(self, key: str) -> str:
        return f"iterlab:lock:{key}"

    async def acquire_lock(self, key: str, *, ttl: int = 30) -> str | None:
        token = secrets.token_hex(16)
        ok = await self._r.set(self._lockkey(key), token, nx=True, ex=ttl)
        return token if ok else None

    async def release_lock(self, key: str, token: str) -> None:
        await self._r.eval(_RELEASE_LUA, 1, self._lockkey(key), token)
