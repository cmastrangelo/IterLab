"""Immutable, versioned prompt registration.

A prompt version is content-addressed and write-once: once
``(lab, slug, version)`` is registered its text can never change. New wording
means a new version file; which version is *live* is a separate, deliberate
pointer (``Lab.prompt_bindings``). This keeps prompt-effectiveness data from
being polluted by silent edits.
"""

from iterlab.prompts.loader import PromptDrift, sync_lab_prompts

__all__ = ["PromptDrift", "sync_lab_prompts"]
