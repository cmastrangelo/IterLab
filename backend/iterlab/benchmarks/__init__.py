"""Benchmark adapters.

A benchmark is defined in the database (``models.Benchmark``) by an ``adapter``
key plus a ``spec`` dict. The adapter is looked up in :mod:`iterlab.benchmarks.registry`
and knows how to (a) render the benchmark's current leaderboard and, later, (b)
evaluate a candidate against it.

Built-in adapters (generic, shipped with IterLab) live in ``benchmarks.builtin``.
Deployment-specific adapters live under the git-ignored instance directory and
register themselves when :func:`iterlab.instance.load_instance_plugins` imports
them at startup.
"""

from iterlab.benchmarks import builtin  # noqa: F401  (registers built-in adapters)
from iterlab.benchmarks.base import (
    BenchmarkAdapter,
    BenchmarkContext,
    Leaderboard,
    LeaderboardColumn,
    LeaderboardRow,
)
from iterlab.benchmarks.registry import get_adapter, list_adapters, register_adapter

__all__ = [
    "BenchmarkAdapter",
    "BenchmarkContext",
    "Leaderboard",
    "LeaderboardColumn",
    "LeaderboardRow",
    "get_adapter",
    "list_adapters",
    "register_adapter",
]
