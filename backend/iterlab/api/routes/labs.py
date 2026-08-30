from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import ConflictError, NotFoundError
from iterlab.models.lab import Lab
from iterlab.models.project import Project
from iterlab.schemas.lab import LabCreate, LabOut

router = APIRouter()


async def _owned_project(session: SessionDep, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.owner_id != user_id:
        raise NotFoundError("project not found")
    return project


@router.get("", response_model=list[LabOut], summary="List labs in a project")
async def list_labs(
    user: CurrentUser,
    session: SessionDep,
    project_id: uuid.UUID,
) -> list[Lab]:
    await _owned_project(session, user.id, project_id)
    rows = await session.scalars(
        select(Lab).where(Lab.project_id == project_id).order_by(Lab.created_at.desc())
    )
    return list(rows)


@router.post(
    "",
    response_model=LabOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lab",
)
async def create_lab(body: LabCreate, user: CurrentUser, session: SessionDep) -> Lab:
    await _owned_project(session, user.id, body.project_id)

    dupe = await session.scalar(
        select(Lab).where(Lab.project_id == body.project_id, Lab.slug == body.slug)
    )
    if dupe is not None:
        raise ConflictError("that project already has a lab with that slug")

    lab = Lab(
        project_id=body.project_id,
        slug=body.slug,
        name=body.name,
        description=body.description,
        repo_url=body.repo_url,
        repo_default_branch=body.repo_default_branch,
        settings=body.settings,
    )
    session.add(lab)
    await session.flush()
    return lab


@router.get("/{lab_id}", response_model=LabOut, summary="Get a lab")
async def get_lab(lab_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Lab:
    lab = await session.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("lab not found")
    await _owned_project(session, user.id, lab.project_id)
    return lab
