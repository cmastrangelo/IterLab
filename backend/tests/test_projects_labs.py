from __future__ import annotations

from httpx import AsyncClient


async def _auth_headers(client: AsyncClient, email: str = "builder@example.com") -> dict:
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 201, resp.text
    return {"authorization": f"Bearer {resp.json()['tokens']['access_token']}"}


async def test_project_and_lab_lifecycle(client: AsyncClient) -> None:
    headers = await _auth_headers(client)

    proj = await client.post(
        "/projects", headers=headers, json={"slug": "demo", "name": "Demo project"}
    )
    assert proj.status_code == 201, proj.text
    project_id = proj.json()["id"]

    listing = await client.get("/projects", headers=headers)
    assert [p["id"] for p in listing.json()] == [project_id]

    lab = await client.post(
        "/labs",
        headers=headers,
        json={
            "project_id": project_id,
            "slug": "baseline",
            "name": "Baseline lab",
            "repo_url": "https://github.com/example/repo.git",
        },
    )
    assert lab.status_code == 201, lab.text
    lab_id = lab.json()["id"]

    labs = await client.get("/labs", headers=headers, params={"project_id": project_id})
    assert [x["id"] for x in labs.json()] == [lab_id]


async def test_projects_are_scoped_to_owner(client: AsyncClient) -> None:
    a = await _auth_headers(client, "a@example.com")
    b = await _auth_headers(client, "b@example.com")

    proj = await client.post("/projects", headers=a, json={"slug": "secret", "name": "A's"})
    pid = proj.json()["id"]

    assert (await client.get(f"/projects/{pid}", headers=b)).status_code == 404
    assert (await client.get("/projects", headers=b)).json() == []


async def test_project_endpoints_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/projects")).status_code == 401
