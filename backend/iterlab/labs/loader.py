"""Provision labs + benchmarks from ``instance/labs/*.yaml`` into the database."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from iterlab.config import get_settings
from iterlab.core.security import generate_token, hash_password
from iterlab.labs.spec import AgentSpec, LabSpec
from iterlab.models.agent import Agent
from iterlab.models.benchmark import Benchmark
from iterlab.models.experiment import Experiment
from iterlab.models.lab import Lab
from iterlab.models.project import Project
from iterlab.models.user import User

logger = logging.getLogger("iterlab.labs")


_T = TypeVar("_T", bound=BaseModel)


def _load_specs(directory: Path, model: type[_T]) -> list[_T]:
    if not directory.is_dir():
        return []
    out: list[_T] = []
    for path in sorted(directory.glob("*.y*ml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        try:
            out.append(model.model_validate(raw))
        except Exception:  # noqa: BLE001
            logger.exception("invalid spec: %s", path)
    return out


def load_lab_specs(instance_dir: Path) -> list[LabSpec]:
    return _load_specs(instance_dir / "labs", LabSpec)


def load_agent_specs(instance_dir: Path) -> list[AgentSpec]:
    return _load_specs(instance_dir / "agents", AgentSpec)


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

    # the lab's workflow lives on a managed Experiment
    if spec.workflow is not None:
        wf = spec.workflow
        exp = await session.scalar(
            select(Experiment).where(Experiment.lab_id == lab.id, Experiment.slug == wf.slug)
        )
        if exp is None:
            exp = Experiment(lab_id=lab.id, slug=wf.slug)
            session.add(exp)
        exp.name = wf.name
        exp.description = wf.description
        exp.workflow = wf.model_dump()
        exp.managed = True
        await session.flush()

    await session.flush()
    logger.info("synced instance lab %r (%d benchmarks)", spec.slug, len(spec.benchmarks))
    return lab


async def sync_agent(session: AsyncSession, spec: AgentSpec) -> Agent:
    owner = await _instance_owner(session)
    agent = await session.scalar(
        select(Agent).where(Agent.owner_id == owner.id, Agent.name == spec.name)
    )
    if agent is None:
        agent = Agent(owner_id=owner.id, name=spec.name)
        session.add(agent)
    agent.description = spec.description
    agent.kind = spec.kind
    agent.managed = True
    if spec.kind == "cli":
        agent.provider = "cli"
        agent.model = None
        agent.credential_ref = None
        agent.params = {
            "command": spec.command,
            "args": spec.args,
            "working_dir": spec.working_dir,
            "env": spec.env,
        }
    else:
        agent.provider = spec.provider
        agent.model = spec.model
        agent.credential_ref = spec.credential_env
        agent.params = spec.params
    await session.flush()
    logger.info("synced instance agent %r (%s)", spec.name, spec.kind)
    return agent


async def sync_instance_labs(session: AsyncSession, instance_dir: Path | None) -> tuple[int, int]:
    if instance_dir is None:
        return 0, 0
    lab_specs = load_lab_specs(instance_dir)
    for lab_spec in lab_specs:
        await sync_lab(session, lab_spec)
    agent_specs = load_agent_specs(instance_dir)
    for agent_spec in agent_specs:
        await sync_agent(session, agent_spec)
    if lab_specs or agent_specs:
        await session.commit()
    return len(lab_specs), len(agent_specs)
