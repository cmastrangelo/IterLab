"""Declarative shape of an instance lab definition (``instance/labs/*.yaml``).

Generic — no field here names any particular external system. A deployment fills
these in privately.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from iterlab.workflows.spec import WorkflowSpec

_SLUG = r"^[a-z0-9][a-z0-9-]{1,78}[a-z0-9]$"


class RepoSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str | None = None
    branch: str = "main"
    # reference (env var name) to a credential, resolved at use time — never the secret
    credential_env: str | None = None


class BenchmarkSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=_SLUG)
    name: str
    description: str | None = None
    adapter: str  # registry key, e.g. "sql_leaderboard"
    primary_metric: str | None = None
    higher_is_better: bool = True
    spec: dict = Field(default_factory=dict)  # adapter-specific config


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=_SLUG)
    name: str
    description: str | None = None
    kind: str  # "cli" | "api"
    # cli
    command: str = "claude"
    flavor: str = "claude"  # "claude" | "codex" | "opencode" | "generic"
    args: list[str] = Field(default_factory=list)
    working_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    # api — and, for cli, the model identifier passed to the CLI (opencode's
    # "provider/model", e.g. "openrouter/z-ai/glm-5.2" or "ollama/qwen2.5-coder")
    provider: str = "anthropic"
    model: str | None = None
    # cli only: model variant / reasoning effort (opencode --variant, e.g. "max")
    variant: str | None = None
    credential_env: str | None = None
    params: dict = Field(default_factory=dict)


class LabSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=_SLUG)
    name: str
    description: str | None = None
    # project the lab belongs to; created under the instance owner if missing
    project_slug: str = Field(pattern=_SLUG, default="instance")
    project_name: str | None = None
    repo: RepoSpec = Field(default_factory=RepoSpec)
    settings: dict = Field(default_factory=dict)
    benchmarks: list[BenchmarkSpec] = Field(default_factory=list)
    # the lab's experiment workflow (steps run per candidate). Optional.
    workflow: WorkflowSpec | None = None
