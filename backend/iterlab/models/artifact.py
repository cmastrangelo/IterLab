from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.enums import ArtifactKind
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Artifact(UUIDPrimaryKey, Timestamps, Base):
    """Metadata for a stored blob. Bytes live in the ArtifactStorage backend.

    ``storage_backend`` + ``storage_key`` are enough to fetch it back regardless
    of whether the backend is the local filesystem, S3, or MinIO.
    """

    __tablename__ = "artifacts"

    # subject links (any subset)
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True
    )
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), index=True
    )

    kind: Mapped[ArtifactKind] = mapped_column(
        String(20), default=ArtifactKind.other, nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(160))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)

    storage_backend: Mapped[str] = mapped_column(String(40), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(600), nullable=False)

    extra: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
