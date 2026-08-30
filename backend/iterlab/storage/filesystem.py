from __future__ import annotations

import hashlib
from pathlib import Path

from iterlab.storage.base import ArtifactStorage, StoredObject


class FilesystemStorage(ArtifactStorage):
    """Stores artifacts under a local root directory. Default backend for dev."""

    name = "filesystem"

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_settings(cls) -> FilesystemStorage:
        from iterlab.config import get_settings

        return cls(get_settings().storage_path)

    def _resolve(self, key: str) -> Path:
        target = (self.root / key.lstrip("/")).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"key escapes storage root: {key!r}")
        return target

    async def put(
        self, key: str, data: bytes, *, content_type: str | None = None
    ) -> StoredObject:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return StoredObject(
            backend=self.name,
            key=key,
            size_bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    async def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()
