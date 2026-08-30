from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from iterlab.db.base import Base
from iterlab.models.enums import CandidateStatus
from iterlab.models.mixins import Timestamps, UUIDPrimaryKey
from iterlab.models.types import JSONMap


class Candidate(UUIDPrimaryKey, Timestamps, Base):
    """The output of one iteration.

    ``parent_id`` links candidates into a lineage tree so IterLab can graph how a
    solution evolved. The actual code change is stored as an artifact; this row
    holds the metadata and headline scores.
    """

    __tablename__ = "candidates"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="SET NULL"), index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agents.id", ondelete="SET NULL"), index=True
    )

    iteration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[CandidateStatus] = mapped_column(
        String(20), default=CandidateStatus.proposed, nullable=False, index=True
    )

    summary: Mapped[str | None] = mapped_column(Text)
    # vcs pointers into the connected repo / working tree
    commit_sha: Mapped[str | None] = mapped_column(String(64))
    branch: Mapped[str | None] = mapped_column(String(200))

    # headline numbers duplicated from metrics for cheap lineage graphs
    score: Mapped[float | None] = mapped_column()
    cost_usd: Mapped[float | None] = mapped_column()
    tokens: Mapped[int | None] = mapped_column(Integer)

    extra: Mapped[dict] = mapped_column(JSONMap, default=dict, nullable=False)
