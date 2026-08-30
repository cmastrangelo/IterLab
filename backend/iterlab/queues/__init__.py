from iterlab.queues.base import KeyValue, Queue
from iterlab.queues.redis_queue import RedisBackend

__all__ = ["KeyValue", "Queue", "RedisBackend", "get_backend"]


def get_backend() -> RedisBackend:
    """Return the coordination backend (Redis today).

    Both :class:`Queue` (ephemeral ready-queues) and :class:`KeyValue`
    (heartbeats, locks, leases) are served by this one backend for now.
    """
    from iterlab.config import get_settings

    return RedisBackend.from_url(get_settings().redis_url)
