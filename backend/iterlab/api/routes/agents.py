from __future__ import annotations

import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from iterlab.api.deps import CurrentUser, SessionDep
from iterlab.core.errors import ConflictError, NotFoundError, PermissionError_
from iterlab.models.agent import Agent
from iterlab.schemas.agent import AgentCreate, AgentOut, AgentUpdate

router = APIRouter()


def _apply_cli(agent: Agent, cli) -> None:
    agent.kind = "cli"
    agent.provider = "cli"
    agent.model = None
    agent.credential_ref = None
    agent.params = cli.model_dump()
    agent.tools = []


def _apply_api(agent: Agent, api) -> None:
    agent.kind = "api"
    agent.provider = api.provider
    agent.model = api.model
    agent.credential_ref = api.credential_env
    agent.params = api.params


@router.get("", response_model=list[AgentOut], summary="List agents")
async def list_agents(user: CurrentUser, session: SessionDep) -> list[AgentOut]:
    rows = await session.scalars(select(Agent).order_by(Agent.created_at.desc()))
    return [AgentOut.from_model(a) for a in rows]


@router.post(
    "",
    response_model=AgentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an agent (kind: cli | api)",
)
async def create_agent(body: AgentCreate, user: CurrentUser, session: SessionDep) -> AgentOut:
    dupe = await session.scalar(
        select(Agent).where(Agent.owner_id == user.id, Agent.name == body.name)
    )
    if dupe is not None:
        raise ConflictError("you already have an agent with that name")

    agent = Agent(owner_id=user.id, name=body.name, description=body.description)
    if body.kind == "cli":
        _apply_cli(agent, body.cli)
    else:
        _apply_api(agent, body.api)
    session.add(agent)
    await session.flush()
    return AgentOut.from_model(agent)


async def _owned_agent(session: SessionDep, user_id: uuid.UUID, agent_id: uuid.UUID) -> Agent:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise NotFoundError("agent not found")
    if agent.owner_id != user_id:
        raise PermissionError_("you do not own that agent")
    if agent.managed:
        raise PermissionError_("this agent is managed by instance config")
    return agent


@router.get("/{agent_id}", response_model=AgentOut, summary="Get an agent")
async def get_agent(agent_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> AgentOut:
    agent = await session.get(Agent, agent_id)
    if agent is None:
        raise NotFoundError("agent not found")
    return AgentOut.from_model(agent)


@router.patch("/{agent_id}", response_model=AgentOut, summary="Update an agent")
async def update_agent(
    agent_id: uuid.UUID, body: AgentUpdate, user: CurrentUser, session: SessionDep
) -> AgentOut:
    agent = await _owned_agent(session, user.id, agent_id)
    if body.name is not None:
        agent.name = body.name
    if body.description is not None:
        agent.description = body.description
    if agent.kind == "cli" and body.cli is not None:
        _apply_cli(agent, body.cli)
    if agent.kind == "api" and body.api is not None:
        _apply_api(agent, body.api)
    await session.flush()
    return AgentOut.from_model(agent)


@router.delete(
    "/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an agent"
)
async def delete_agent(agent_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    agent = await _owned_agent(session, user.id, agent_id)
    await session.delete(agent)
