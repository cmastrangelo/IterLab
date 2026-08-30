"""Artifact storage abstraction.

The controller and workers only ever deal in ``(backend, key)`` pairs plus this
interface, so the filesystem backend can be replaced with S3/MinIO/GCS later
without touching call sites. Keys are opaque, ``/``-delimited paths.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass(slots=True)
class StoredObject:
    backend: str
    key: str
    size_bytes: int
    sha256: str
    content_type: str | None = None


class ArtifactStorage(abc.ABC):
    name: str = "base"

    @classmethod
    @abc.abstractmethod
    def from_settings(cls) -> ArtifactStorage: ...

    @abc.abstractmethod
    async def put(
        self, key: str, data: bytes, *, content_type: str | None = None
    ) -> StoredObject: ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes: ...

    @abc.abstractmethod
    async def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    async def exists(self, key: str) -> bool: ...

    async def presigned_url(self, key: str, *, expires_in: int = 3600) -> str | None:
        """Return a direct download URL if the backend supports it, else None."""
        return None
