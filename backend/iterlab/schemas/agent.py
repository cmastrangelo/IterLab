from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AgentKind = Literal["cli", "api"]


class CliConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    command: str = "claude"
    # how the CLI is driven headlessly (prompt/session/resume flags, output
    # parsing). "generic" just runs `command args prompt`. Consumers that need
    # session continuity look at this.
    flavor: str = "claude"  # "claude" | "codex" | "opencode" | "generic"
    # model identifier passed to the CLI (e.g. opencode's "provider/model" like
    # "openrouter/z-ai/glm-5.2", or "ollama/qwen2.5-coder" for a local model).
    # Lets several agents share one CLI while each pins its own model.
    model: str | None = None
    args: list[str] = Field(default_factory=list)
    working_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class ApiConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "anthropic"
    model: str | None = None
    # env var name holding the API key (never the key itself)
    credential_env: str | None = None
    params: dict = Field(default_factory=dict)


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    kind: AgentKind
    cli: CliConfig | None = None
    api: ApiConfig | None = None

    @model_validator(mode="after")
    def _one_config(self) -> AgentCreate:
        if self.kind == "cli" and self.api is not None:
            raise ValueError("cli agent must not carry an 'api' config")
        if self.kind == "api" and self.cli is not None:
            raise ValueError("api agent must not carry a 'cli' config")
        if self.kind == "cli" and self.cli is None:
            self.cli = CliConfig()
        if self.kind == "api" and self.api is None:
            self.api = ApiConfig()
        return self


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    cli: CliConfig | None = None
    api: ApiConfig | None = None


class AgentOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    description: str | None
    kind: AgentKind
    managed: bool
    cli: CliConfig | None = None
    api: ApiConfig | None = None
    created_at: datetime

    @classmethod
    def from_model(cls, agent) -> AgentOut:
        cli = api = None
        if agent.kind == "cli":
            cli = CliConfig(**(agent.params or {}))
        else:
            api = ApiConfig(
                provider=agent.provider or "anthropic",
                model=agent.model,
                credential_env=agent.credential_ref,
                params=agent.params or {},
            )
        return cls(
            id=agent.id,
            owner_id=agent.owner_id,
            name=agent.name,
            description=agent.description,
            kind=agent.kind,
            managed=agent.managed,
            cli=cli,
            api=api,
            created_at=agent.created_at,
        )
