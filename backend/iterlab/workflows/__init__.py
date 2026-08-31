"""Workflow steps.

A lab defines a *workflow* — an ordered list of steps — in its instance config.
Each step names a **step handler** (registry key) plus a config dict. Handlers
are registered like benchmark adapters: built-ins here, deployment-specific ones
under ``instance/adapters/``.

IterLab is the harness; the workflow (which steps, in what order, with what
prompts) is entirely the deployment's to define.
"""

from iterlab.workflows.base import StepContext, StepHandler, StepResult
from iterlab.workflows.registry import get_step_handler, list_step_handlers, register_step_handler
from iterlab.workflows.spec import StepSpec, WorkflowSpec

__all__ = [
    "StepContext",
    "StepHandler",
    "StepResult",
    "StepSpec",
    "WorkflowSpec",
    "get_step_handler",
    "list_step_handlers",
    "register_step_handler",
]
