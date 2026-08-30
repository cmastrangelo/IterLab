from __future__ import annotations

import pytest
from httpx import AsyncClient

REGISTER = {
    "email": "ada@example.com",
    "password": "correct-horse-battery-staple",
    "full_name": "Ada Lovelace",
}


async def _register(client: AsyncClient, **overrides) -> dict:
    payload = {**REGISTER, **overrides}
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_register_returns_user_and_tokens(client: AsyncClient) -> None:
    body = await _register(client)
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["is_active"] is True
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["tokens"]["token_type"] == "bearer"


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post("/auth/register", json=REGISTER)
    assert resp.status_code == 409


async def test_register_rejects_weak_password(client: AsyncClient) -> None:
    resp = await client.post("/auth/register", json={**REGISTER, "password": "short"})
    assert resp.status_code == 422


async def test_login_and_me(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        "/auth/login", json={"email": REGISTER["email"], "password": REGISTER["password"]}
    )
    assert resp.status_code == 200
    access = resp.json()["tokens"]["access_token"]

    me = await client.get("/auth/me", headers={"authorization": f"Bearer {access}"})
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER["email"]


async def test_login_wrong_password_is_401(client: AsyncClient) -> None:
    await _register(client)
    resp = await client.post(
        "/auth/login", json={"email": REGISTER["email"], "password": "nope-nope-nope"}
    )
    assert resp.status_code == 401


async def test_me_requires_token(client: AsyncClient) -> None:
    assert (await client.get("/auth/me")).status_code == 401


async def test_refresh_rotates_and_invalidates_old_token(client: AsyncClient) -> None:
    body = await _register(client)
    old_refresh = body["tokens"]["refresh_token"]

    first = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["tokens"]["refresh_token"]
    assert new_refresh != old_refresh

    # reusing the old (rotated) token must fail
    replay = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert replay.status_code == 401

    # and the reuse-detection revokes the whole chain, including the new token
    after = await client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    body = await _register(client)
    refresh = body["tokens"]["refresh_token"]

    assert (await client.post("/auth/logout", json={"refresh_token": refresh})).status_code == 204
    assert (
        await client.post("/auth/refresh", json={"refresh_token": refresh})
    ).status_code == 401


@pytest.mark.parametrize("path", ["/healthz"])
async def test_health(client: AsyncClient, path: str) -> None:
    resp = await client.get(path)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
