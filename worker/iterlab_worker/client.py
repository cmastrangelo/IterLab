from __future__ import annotations

import json
from pathlib import Path

import httpx

from iterlab_worker.config import WorkerSettings


class WorkerIdentity:
    def __init__(self, worker_id: str, token: str):
        self.worker_id = worker_id
        self.token = token

    @classmethod
    def load(cls, path: str) -> "WorkerIdentity | None":
        p = Path(path)
        if not p.is_file():
            return None
        data = json.loads(p.read_text())
        return cls(data["worker_id"], data["token"])

    def save(self, path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"worker_id": self.worker_id, "token": self.token}))
        p.chmod(0o600)


class ControllerClient:
    def __init__(self, settings: WorkerSettings):
        self.settings = settings
        self._http = httpx.Client(base_url=settings.base_url, timeout=30)

    def register(self) -> WorkerIdentity:
        if not self.settings.enroll_token:
            raise RuntimeError("ITERLAB_WORKER_ENROLL_TOKEN is required for first registration")
        resp = self._http.post(
            "/workers/register",
            headers={"authorization": f"Bearer {self.settings.enroll_token}"},
            json={
                "name": self.settings.name,
                "resources": {
                    "cpu": self.settings.cpu,
                    "memory_mb": self.settings.memory_mb,
                    "gpu": self.settings.gpu,
                    "vram_mb": self.settings.vram_mb,
                },
                "labels": self.settings.label_map,
                "agent_version": _agent_version(),
            },
        )
        resp.raise_for_status()
        body = resp.json()
        return WorkerIdentity(str(body["worker_id"]), body["worker_token"])

    def heartbeat(self, identity: WorkerIdentity, *, status: str = "idle") -> dict:
        resp = self._http.post(
            f"/workers/{identity.worker_id}/heartbeat",
            headers={"authorization": f"Bearer {identity.token}"},
            json={
                "status": status,
                "resources_available": {
                    "cpu": self.settings.cpu,
                    "memory_mb": self.settings.memory_mb,
                    "gpu": self.settings.gpu,
                    "vram_mb": self.settings.vram_mb,
                },
                "tasks": [],
            },
        )
        resp.raise_for_status()
        return resp.json()

    def pull_task(self, identity: WorkerIdentity) -> dict | None:
        resp = self._http.get(
            f"/workers/{identity.worker_id}/tasks",
            headers={"authorization": f"Bearer {identity.token}"},
        )
        if resp.status_code == 204:
            return None
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()


def _agent_version() -> str:
    from iterlab_worker import __version__

    return __version__
