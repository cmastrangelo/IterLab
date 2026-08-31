from __future__ import annotations

from httpx import AsyncClient


async def _auth(client: AsyncClient, email: str = "agent@example.com") -> dict:
    r = await client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    return {"authorization": f"Bearer {r.json()['tokens']['access_token']}"}


async def test_create_cli_agent(client: AsyncClient) -> None:
    headers = await _auth(client)
    resp = await client.post(
        "/agents",
        headers=headers,
        json={
            "name": "claude cli",
            "kind": "cli",
            "cli": {"command": "claude", "args": ["-p"], "working_dir": "/repo"},
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["kind"] == "cli"
    assert body["cli"] == {
        "command": "claude",
        "flavor": "claude",
        "args": ["-p"],
        "working_dir": "/repo",
        "env": {},
    }
    assert body["api"] is None
    assert body["managed"] is False


async def test_create_cli_agent_with_flavor(client: AsyncClient) -> None:
    headers = await _auth(client, "flavor@example.com")
    resp = await client.post(
        "/agents",
        headers=headers,
        json={"name": "codex", "kind": "cli", "cli": {"command": "codex", "flavor": "codex"}},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["cli"]["flavor"] == "codex"


async def test_create_api_agent_defaults_and_credential_ref(client: AsyncClient) -> None:
    headers = await _auth(client)
    resp = await client.post(
        "/agents",
        headers=headers,
        json={
            "name": "sonnet",
            "kind": "api",
            "api": {"model": "claude-sonnet-5", "credential_env": "ANTHROPIC_API_KEY"},
        },
    )
    assert resp.status_code == 201, resp.text
    api = resp.json()["api"]
    assert api["provider"] == "anthropic"
    assert api["model"] == "claude-sonnet-5"
    assert api["credential_env"] == "ANTHROPIC_API_KEY"


async def test_cli_agent_rejects_api_config(client: AsyncClient) -> None:
    headers = await _auth(client)
    resp = await client.post(
        "/agents",
        headers=headers,
        json={"name": "x", "kind": "cli", "api": {"provider": "anthropic"}},
    )
    assert resp.status_code == 422


async def test_update_and_list(client: AsyncClient) -> None:
    headers = await _auth(client)
    created = (
        await client.post(
            "/agents", headers=headers, json={"name": "a1", "kind": "cli"}
        )
    ).json()

    patched = await client.patch(
        f"/agents/{created['id']}",
        headers=headers,
        json={"description": "runs claude", "cli": {"command": "claude", "args": ["--yolo"]}},
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "runs claude"
    assert patched.json()["cli"]["args"] == ["--yolo"]

    listing = await client.get("/agents", headers=headers)
    assert [a["name"] for a in listing.json()] == ["a1"]


async def test_agents_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/agents")).status_code == 401
