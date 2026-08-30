from iterlab.storage.base import ArtifactStorage, StoredObject
from iterlab.storage.filesystem import FilesystemStorage

__all__ = ["ArtifactStorage", "StoredObject", "FilesystemStorage", "get_storage"]

_BACKENDS = {"filesystem": FilesystemStorage}


def get_storage(backend: str | None = None) -> ArtifactStorage:
    from iterlab.config import get_settings

    name = backend or get_settings().storage_backend
    try:
        return _BACKENDS[name].from_settings()
    except KeyError:
        raise ValueError(f"unknown storage backend: {name!r}") from None
