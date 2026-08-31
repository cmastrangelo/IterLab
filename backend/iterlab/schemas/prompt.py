from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lab_id: uuid.UUID
    slug: str
    version: int
    text: str
    digest: str
    created_at: datetime

    # usage stats over candidates whose agent step used this prompt version
    uses: int = 0
    scored: int = 0
    avg_score: float | None = None
    best_score: float | None = None
