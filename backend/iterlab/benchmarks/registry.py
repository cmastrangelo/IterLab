"""Benchmark adapter registry."""

from __future__ import annotations

from iterlab.benchmarks.base import BenchmarkAdapter, BenchmarkConfigError

_ADAPTERS: dict[str, BenchmarkAdapter] = {}


def register_adapter(adapter: BenchmarkAdapter | type[BenchmarkAdapter]) -> None:
    instance = adapter() if isinstance(adapter, type) else adapter
    if not instance.key or instance.key == "base":
        raise ValueError(f"adapter {instance!r} must define a unique 'key'")
    _ADAPTERS[instance.key] = instance


def get_adapter(key: str) -> BenchmarkAdapter:
    try:
        return _ADAPTERS[key]
    except KeyError:
        raise BenchmarkConfigError(
            f"unknown benchmark adapter {key!r}; registered: {sorted(_ADAPTERS)}"
        ) from None


def list_adapters() -> list[dict[str, str]]:
    return [{"key": a.key, "summary": a.summary} for a in _ADAPTERS.values()]
