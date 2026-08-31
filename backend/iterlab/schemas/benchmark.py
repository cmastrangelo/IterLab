from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BenchmarkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lab_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    adapter: str
    primary_metric: str | None
    higher_is_better: bool
    managed: bool
    created_at: datetime
