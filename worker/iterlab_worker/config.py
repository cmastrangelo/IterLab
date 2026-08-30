from __future__ import annotations

import os
from pathlib import Path

import psutil
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_state_file() -> str:
    return str(Path.home() / ".iterlab" / "worker.json")


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ITERLAB_WORKER_", extra="ignore")

    controller_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    enroll_token: str | None = None
    name: str = Field(default_factory=lambda: os.uname().nodename)
    state_file: str = Field(default_factory=_default_state_file)

    cpu: float = Field(default_factory=lambda: float(psutil.cpu_count() or 1))
    memory_mb: int = Field(default_factory=lambda: int(psutil.virtual_memory().total / 1_000_000))
    gpu: int = 0
    vram_mb: int = 0
    labels: str | None = None  # "k=v,k=v"

    @property
    def base_url(self) -> str:
        return f"{self.controller_url.rstrip('/')}{self.api_prefix}"

    @property
    def label_map(self) -> dict[str, str]:
        return parse_labels(self.labels)


def parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    out: dict[str, str] = {}
    for pair in raw.split(","):
        if "=" in pair:
            k, v = pair.split("=", 1)
            out[k.strip()] = v.strip()
    return out
