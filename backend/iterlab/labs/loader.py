"""Provision labs + benchmarks from ``instance/labs/*.yaml`` into the database."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.config import get_settings
from iterlab.core.security import generate_token, hash_password
from iterlab.labs.spec import LabSpec
from iterlab.models.benchmark import Benchmark
from iterlab.models.lab import Lab
from iterlab.models.project import Project
from iterlab.models.user import User

logger = logging.getLogger("iterlab.labs")


def load_lab_specs(instance_dir: Path) -> list[LabSpec]:
    labs_dir = instance_dir / "labs"
    if not labs_dir.is_dir():
        return []
    specs: list[LabSpec] = []
    for path in sorted(labs_dir.glob("*.y*ml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            specs.append(LabSpec.model_validate(raw))
        except Exception:  # noqa: BLE001
            logger.exception("invalid lab spec: %s", path)
    return specs


async def _instance_owner(session: AsyncSession) -> User:
    email = get_settings().instance_owner_email.strip().lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name="IterLab instance",
            password_hash=hash_password(generate_token()),  # unusable login
            is_active=True,
        )
        session.add(user)
        await session.flush()
        logger.info("created instance owner %s", email)
    return user


async def sync_lab(session: AsyncSession, spec: LabSpec) -> Lab:
    owner = await _instance_owner(session)

    project = await session.scalar(
        select(Project).where(Project.owner_id == owner.id, Project.slug == spec.project_slug)
    )
    if project is None:
        project = Project(
            owner_id=owner.id,
            slug=spec.project_slug,
            name=spec.project_name or spec.project_slug.replace("-", " ").title(),
        )
        session.add(project)
        await session.flush()

    lab = await session.scalar(
        select(Lab).where(Lab.project_id == project.id, Lab.slug == spec.slug)
    )
    if lab is None:
        lab = Lab(project_id=project.id, slug=spec.slug)
        session.add(lab)
    lab.name = spec.name
    lab.description = spec.description
    lab.repo_url = spec.repo.url
    lab.repo_default_branch = spec.repo.branch
    lab.repo_credential_ref = spec.repo.credential_env
    lab.settings = spec.settings
    lab.source = "instance"
    await session.flush()

    seen: set[str] = set()
    for b in spec.benchmarks:
        seen.add(b.slug)
        bench = await session.scalar(
            select(Benchmark).where(Benchmark.lab_id == lab.id, Benchmark.slug == b.slug)
        )
        if bench is None:
            bench = Benchmark(lab_id=lab.id, slug=b.slug)
            session.add(bench)
        bench.name = b.name
        bench.description = b.description
        bench.adapter = b.adapter
        bench.spec = {**b.spec, "_slug": b.slug}
        bench.primary_metric = b.primary_metric
        bench.higher_is_better = b.higher_is_better
        bench.managed = True

    # drop managed benchmarks that vanished from the spec
    existing = await session.scalars(
        select(Benchmark).where(Benchmark.lab_id == lab.id, Benchmark.managed.is_(True))
    )
    for bench in existing:
        if bench.slug not in seen:
            await session.delete(bench)

    await session.flush()
    logger.info("synced instance lab %r (%d benchmarks)", spec.slug, len(spec.benchmarks))
    return lab


async def sync_instance_labs(session: AsyncSession, instance_dir: Path | None) -> int:
    if instance_dir is None:
        return 0
    specs = load_lab_specs(instance_dir)
    for spec in specs:
        await sync_lab(session, spec)
    if specs:
        await session.commit()
    return len(specs)
