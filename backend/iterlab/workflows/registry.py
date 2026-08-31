from __future__ import annotations

from iterlab.workflows.base import StepError, StepHandler

_HANDLERS: dict[str, StepHandler] = {}


def register_step_handler(handler: StepHandler | type[StepHandler]) -> None:
    instance = handler() if isinstance(handler, type) else handler
    if not instance.key or instance.key == "base":
        raise ValueError(f"step handler {instance!r} must define a unique 'key'")
    _HANDLERS[instance.key] = instance


def get_step_handler(key: str) -> StepHandler:
    try:
        return _HANDLERS[key]
    except KeyError:
        raise StepError(
            f"unknown step handler {key!r}; registered: {sorted(_HANDLERS)}"
        ) from None


def list_step_handlers() -> list[dict[str, str]]:
    return [{"key": h.key, "summary": h.summary} for h in _HANDLERS.values()]
