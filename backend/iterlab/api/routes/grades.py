from __future__ import annotations

import uuid

from fastapi import APIRouter

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.runs.grades import compute_lab_grades
from iterlab.schemas.grades import LabGrades

# routes mounted under /labs
lab_grades = APIRouter()


@lab_grades.get(
    "/{lab_id}/grades",
    response_model=LabGrades,
    summary="Rank this lab's agents and prompt versions by frontier contribution",
)
async def get_lab_grades(lab_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabGrades:
    return await compute_lab_grades(session, lab_id)
