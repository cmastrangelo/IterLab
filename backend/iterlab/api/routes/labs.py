from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import ConflictError, NotFoundError, PermissionError_
from iterlab.models.benchmark import Benchmark
from iterlab.models.lab import Lab
from iterlab.models.project import Project
from iterlab.schemas.benchmark import BenchmarkOut
from iterlab.schemas.lab import LabCreate, LabDetailOut, LabOut

router = APIRouter()

# NOTE: reads are open to any authenticated user for this phase (single-operator
# deployments). Per-project RBAC comes with the auth work.


@router.get("", response_model=list[LabOut], summary="List labs")
async def list_labs(
    user: CurrentUser,
    session: SessionDep,
    project_id: uuid.UUID | None = None,
) -> list[Lab]:
    stmt = select(Lab).order_by(Lab.created_at.desc())
    if project_id is not None:
        stmt = stmt.where(Lab.project_id == project_id)
    return list(await session.scalars(stmt))


@router.post(
    "",
    response_model=LabOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lab",
)
async def create_lab(body: LabCreate, user: CurrentUser, session: SessionDep) -> Lab:
    project = await session.get(Project, body.project_id)
    if project is None:
        raise NotFoundError("project not found")
    if project.owner_id != user.id:
        raise PermissionError_("you do not own that project")

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
        source="manual",
    )
    session.add(lab)
    await session.flush()
    return lab


async def _get_lab(session: SessionDep, lab_id: uuid.UUID) -> Lab:
    lab = await session.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("lab not found")
    return lab


@router.get("/{lab_id}", response_model=LabDetailOut, summary="Get a lab with its benchmarks")
async def get_lab(lab_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LabDetailOut:
    lab = await _get_lab(session, lab_id)
    benchmarks = await session.scalars(
        select(Benchmark).where(Benchmark.lab_id == lab.id).order_by(Benchmark.created_at)
    )
    detail = LabDetailOut.model_validate(lab)
    detail.benchmarks = [BenchmarkOut.model_validate(b) for b in benchmarks]
    return detail


@router.get(
    "/{lab_id}/benchmarks",
    response_model=list[BenchmarkOut],
    summary="List a lab's benchmarks",
)
async def list_lab_benchmarks(
    lab_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[Benchmark]:
    await _get_lab(session, lab_id)
    return list(
        await session.scalars(
            select(Benchmark).where(Benchmark.lab_id == lab_id).order_by(Benchmark.created_at)
        )
    )
