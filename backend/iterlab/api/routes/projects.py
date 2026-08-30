from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import ConflictError, NotFoundError
from iterlab.models.project import Project
from iterlab.schemas.project import ProjectCreate, ProjectOut

router = APIRouter()


@router.get("", response_model=list[ProjectOut], summary="List your projects")
async def list_projects(user: CurrentUser, session: SessionDep) -> list[Project]:
    rows = await session.scalars(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    )
    return list(rows)


@router.post(
    "",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    body: ProjectCreate, user: CurrentUser, session: SessionDep
) -> Project:
    dupe = await session.scalar(
        select(Project).where(Project.owner_id == user.id, Project.slug == body.slug)
    )
    if dupe is not None:
        raise ConflictError("you already have a project with that slug")

    project = Project(
        owner_id=user.id,
        slug=body.slug,
        name=body.name,
        description=body.description,
    )
    session.add(project)
    await session.flush()
    return project


@router.get("/{project_id}", response_model=ProjectOut, summary="Get a project")
async def get_project(
    project_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Project:
    project = await session.get(Project, project_id)
    if project is None or project.owner_id != user.id:
        raise NotFoundError("project not found")
    return project
