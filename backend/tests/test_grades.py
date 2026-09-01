from __future__ import annotations

import hashlib

from iterlab.db.session import get_sessionmaker
from iterlab.labs.loader import sync_lab
from iterlab.labs.spec import LabSpec
from iterlab.models.candidate import Candidate
from iterlab.models.experiment import Experiment, Run
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.runs.grades import compute_lab_grades


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


async def test_compute_lab_grades_frontier_delta_and_iterate_lift() -> None:
    async with get_sessionmaker()() as session:
        spec = LabSpec(slug="grades-lab", name="Grades Lab", project_slug="grades-proj")
        lab = await sync_lab(session, spec)
        exp = Experiment(lab_id=lab.id, slug="e", name="e", workflow={})
        session.add(exp)
        await session.flush()

        initial = Prompt(
            lab_id=lab.id, slug="initial", version=0, text="go", digest=_digest("go")
        )
        iterate = Prompt(
            lab_id=lab.id, slug="iterate", version=0, text="more", digest=_digest("more")
        )
        session.add_all([initial, iterate])
        await session.flush()

        # run A: Agent X, one shot, score 60 -> first ever run, sets the frontier
        run_a = Run(experiment_id=exp.id, status="succeeded", iteration=1)
        session.add(run_a)
        await session.flush()
        cand_a0 = Candidate(run_id=run_a.id, iteration=0, score=60.0, extra={"name": "a0"})
        session.add(cand_a0)
        session.add(
            RunStep(
                run_id=run_a.id, iteration=0, position=0, handler="agent", status="succeeded",
                config={}, output={"agent": "Agent X"}, prompt_id=initial.id,
            )
        )

        # run B: Agent Y, two iterations — iter0 falls short of the frontier,
        # iter1 (iterate prompt) lifts well above run B's own iter0
        run_b = Run(experiment_id=exp.id, status="succeeded", iteration=2)
        session.add(run_b)
        await session.flush()
        cand_b0 = Candidate(run_id=run_b.id, iteration=0, score=55.0, extra={"name": "b0"})
        cand_b1 = Candidate(run_id=run_b.id, iteration=1, score=58.0, extra={"name": "b1"})
        session.add_all([cand_b0, cand_b1])
        session.add_all(
            [
                RunStep(
                    run_id=run_b.id, iteration=0, position=0, handler="agent", status="succeeded",
                    config={}, output={"agent": "Agent Y"}, prompt_id=initial.id,
                ),
                RunStep(
                    run_id=run_b.id, iteration=1, position=0, handler="agent", status="succeeded",
                    config={}, output={"agent": "Agent Y"}, prompt_id=iterate.id,
                ),
            ]
        )
        await session.commit()
        lab_id = lab.id

    async with get_sessionmaker()() as session:
        grades = await compute_lab_grades(session, lab_id)

    by_agent = {a.agent: a for a in grades.agents}
    assert by_agent["Agent X"].runs == 1
    assert by_agent["Agent X"].avg_score == 60.0
    assert by_agent["Agent X"].avg_delta is None  # first run ever: no frontier to beat
    assert by_agent["Agent X"].new_best_rate == 1.0

    assert by_agent["Agent Y"].runs == 1
    assert by_agent["Agent Y"].candidates == 2
    assert by_agent["Agent Y"].avg_score == 56.5
    assert by_agent["Agent Y"].avg_delta == -2.0  # best (58) vs frontier (60)
    assert by_agent["Agent Y"].new_best_rate == 0.0

    by_slug = {(p.slug, p.version): p for p in grades.prompts}
    ini = by_slug[("initial", 0)]
    assert ini.uses == 2
    assert ini.basis == "cold start"
    assert ini.avg_delta == -5.0  # only run B's iter0 counted (run A had no frontier yet)
    assert ini.new_best_rate == 0.5  # run A's iter0 was a new best; run B's wasn't

    itr = by_slug[("iterate", 0)]
    assert itr.uses == 1
    assert itr.basis == "iterate lift"
    assert itr.avg_delta == 3.0  # 58 - 55, within run B
    assert itr.new_best_rate == 0.0  # 58 never beat the all-time best of 60

    assert "small sample" in grades.note.lower()


async def test_compute_lab_grades_handles_no_runs() -> None:
    async with get_sessionmaker()() as session:
        spec = LabSpec(slug="empty-grades-lab", name="Empty", project_slug="grades-proj-2")
        lab = await sync_lab(session, spec)
        await session.commit()
        lab_id = lab.id

    async with get_sessionmaker()() as session:
        grades = await compute_lab_grades(session, lab_id)

    assert grades.agents == []
    assert grades.prompts == []
    assert grades.note == "no runs yet"
