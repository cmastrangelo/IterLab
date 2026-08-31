from __future__ import annotations

import uuid

from fastapi import APIRouter
from sqlalchemy import func, select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import NotFoundError
from iterlab.models.candidate import Candidate
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.schemas.prompt import PromptOut

router = APIRouter()

# routes mounted under /labs
lab_prompts = APIRouter()


@lab_prompts.get(
    "/{lab_id}/prompts",
    response_model=list[PromptOut],
    summary="Every prompt version for a lab, with per-version candidate stats",
)
async def list_lab_prompts(
    lab_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[PromptOut]:
    prompts = list(
        await session.scalars(
            select(Prompt)
            .where(Prompt.lab_id == lab_id)
            .order_by(Prompt.slug, Prompt.version)
        )
    )
    if not prompts:
        return []

    # candidate whose (run, iteration) matches an agent step that used the prompt
    stats_rows = await session.execute(
        select(
            RunStep.prompt_id,
            func.count(func.distinct(Candidate.id)),
            func.count(Candidate.score),
            func.avg(Candidate.score),
            func.max(Candidate.score),
        )
        .join(
            Candidate,
            (Candidate.run_id == RunStep.run_id) & (Candidate.iteration == RunStep.iteration),
        )
        .where(RunStep.prompt_id.in_([p.id for p in prompts]))
        .group_by(RunStep.prompt_id)
    )
    stats = {
        row[0]: {"uses": row[1], "scored": row[2], "avg": row[3], "best": row[4]}
        for row in stats_rows
    }

    out: list[PromptOut] = []
    for p in prompts:
        s = stats.get(p.id, {})
        item = PromptOut.model_validate(p)
        item.uses = int(s.get("uses") or 0)
        item.scored = int(s.get("scored") or 0)
        item.avg_score = round(float(s["avg"]), 2) if s.get("avg") is not None else None
        item.best_score = float(s["best"]) if s.get("best") is not None else None
        out.append(item)
    return out


@router.get("/{prompt_id}", response_model=PromptOut, summary="A single prompt version")
async def get_prompt(prompt_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> Prompt:
    prompt = await session.get(Prompt, prompt_id)
    if prompt is None:
        raise NotFoundError("prompt not found")
    return prompt
