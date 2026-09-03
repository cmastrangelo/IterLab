from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select

from iterlab.db.session import get_sessionmaker
from iterlab.labs.loader import sync_lab
from iterlab.labs.spec import LabSpec, PromptBindings
from iterlab.models.candidate import Candidate
from iterlab.models.experiment import Experiment, Run
from iterlab.models.lab import Lab
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.prompts import PromptDrift, sync_lab_prompts
from iterlab.runs.executor import _resolve_prompt, execute_run
from iterlab.workflows.base import (
    CandidateInfo,
    PromptRef,
    StepContext,
    StepHandler,
    StepResult,
)
from iterlab.workflows.registry import register_step_handler
from iterlab.workflows.spec import StepSpec, WorkflowSpec


class _PromptAgent(StepHandler):
    key = "test_prompt_agent"

    async def run(self, ctx: StepContext) -> StepResult:
        bound = ctx.prompt("initial")
        assert bound is not None
        return StepResult(
            output={"pv": bound["version"]},
            candidate=CandidateInfo(name="sol.py", score=1.0),
            prompt=PromptRef(slug="initial", template=bound["text"], version=bound["version"]),
        )


register_step_handler(_PromptAgent)


def _write(root: Path, slug: str, version: int, text: str) -> None:
    d = root / slug
    d.mkdir(parents=True, exist_ok=True)
    (d / f"v{version}.md").write_text(text)


async def _sync(instance_dir: Path, slug: str, active: dict[str, int]) -> uuid.UUID:
    """(Re)sync a lab from `instance_dir/prompts/<slug>/...`; return the lab id."""
    spec = LabSpec(
        slug=slug,
        name=slug,
        project_slug="prompt-proj",
        prompts=PromptBindings(active=active),
        workflow=WorkflowSpec(
            slug="iterate", name="iterate", iterations=1,
            steps=[StepSpec(handler="test_prompt_agent")],
        ),
    )
    async with get_sessionmaker()() as session:
        lab = await sync_lab(session, spec, instance_dir)
        await session.commit()
        return lab.id


async def test_registers_version_files_and_binds_active(tmp_path: Path) -> None:
    root = tmp_path / "prompts" / "reglab"
    _write(root, "initial", 0, "the first prompt\n")
    _write(root, "initial", 1, "the aggressive prompt\n")

    lab_id = await _sync(tmp_path, "reglab", {"initial": 1})

    async with get_sessionmaker()() as session:
        rows = list(
            await session.scalars(
                select(Prompt).where(Prompt.lab_id == lab_id).order_by(Prompt.version)
            )
        )
        lab = await session.get(Lab, lab_id)
    assert [(r.slug, r.version, r.text) for r in rows] == [
        ("initial", 0, "the first prompt\n"),
        ("initial", 1, "the aggressive prompt\n"),
    ]
    assert lab is not None and lab.prompt_bindings == {"initial": 1}


async def test_editing_a_registered_version_is_drift_not_a_new_version(tmp_path: Path) -> None:
    root = tmp_path / "prompts" / "driftlab"
    _write(root, "initial", 0, "original text\n")
    await _sync(tmp_path, "driftlab", {"initial": 0})

    (root / "initial" / "v0.md").write_text("SNEAKILY CHANGED\n")  # tamper
    lab_id = await _sync(tmp_path, "driftlab", {"initial": 0})  # re-sync

    async with get_sessionmaker()() as session:
        rows = list(await session.scalars(select(Prompt).where(Prompt.lab_id == lab_id)))
    # exactly one version, still the original — no silent re-version
    assert [(r.version, r.text) for r in rows] == [(0, "original text\n")]


async def test_drift_can_be_made_fatal(tmp_path: Path, monkeypatch) -> None:
    import iterlab.prompts.loader as loader

    root = tmp_path / "prompts" / "fatallab"
    _write(root, "initial", 0, "v0\n")
    await _sync(tmp_path, "fatallab", {"initial": 0})
    (root / "initial" / "v0.md").write_text("changed\n")

    monkeypatch.setattr(loader, "_DRIFT_FATAL", True)
    async with get_sessionmaker()() as session:
        lab = await session.scalar(select(Lab).where(Lab.slug == "fatallab"))
        with pytest.raises(PromptDrift):
            await sync_lab_prompts(session, lab, tmp_path)


async def test_new_version_file_registers_cleanly(tmp_path: Path) -> None:
    root = tmp_path / "prompts" / "growlab"
    _write(root, "initial", 0, "v0\n")
    _write(root, "initial", 1, "v1\n")
    await _sync(tmp_path, "growlab", {"initial": 1})

    _write(root, "initial", 2, "v2 the new one\n")
    lab_id = await _sync(tmp_path, "growlab", {"initial": 2})

    async with get_sessionmaker()() as session:
        rows = list(
            await session.scalars(
                select(Prompt).where(Prompt.lab_id == lab_id).order_by(Prompt.version)
            )
        )
        lab = await session.get(Lab, lab_id)
    assert [r.version for r in rows] == [0, 1, 2]
    assert lab is not None and lab.prompt_bindings == {"initial": 2}


async def test_run_records_the_active_prompt_version(tmp_path: Path) -> None:
    root = tmp_path / "prompts" / "runlab"
    _write(root, "initial", 0, "v0\n")
    _write(root, "initial", 1, "v1\n")
    lab_id = await _sync(tmp_path, "runlab", {"initial": 1})

    async with get_sessionmaker()() as session:
        exp = await session.scalar(select(Experiment).where(Experiment.lab_id == lab_id))
        run = Run(experiment_id=exp.id, status="pending", iteration=1, context={"iterations": 1})
        session.add(run)
        await session.commit()
        run_id = run.id

    async with get_sessionmaker()() as session:
        await execute_run(session, run_id)

    async with get_sessionmaker()() as session:
        cand = await session.scalar(select(Candidate).where(Candidate.run_id == run_id))
        step = await session.scalar(select(RunStep).where(RunStep.run_id == run_id))
        p = await session.get(Prompt, step.prompt_id)
    assert cand.extra["prompt_version"] == 1
    assert p.version == 1 and p.text == "v1\n"


async def test_unregistered_prompt_ref_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "prompts" / "strictlab"
    _write(root, "initial", 0, "only v0\n")
    lab_id = await _sync(tmp_path, "strictlab", {"initial": 0})

    async with get_sessionmaker()() as session:
        with pytest.raises(Exception, match="not registered"):
            await _resolve_prompt(
                session, lab_id, PromptRef(slug="initial", template="made up", version=9)
            )
