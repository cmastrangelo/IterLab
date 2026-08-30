# IterLab web interface

Planned: **TypeScript + Next.js/React** dashboard for:

- login / session handling against `POST /api/v1/auth/*` (access token in memory,
  refresh token rotation)
- projects & labs: create, configure basic settings, connect a repository
- experiments / runs: list, inspect lineage, view candidate graphs
- workers: registration status, resources, heartbeats
- metrics: performance / cost / model-effectiveness over time

Not yet scaffolded. The backend API it will consume is live at
`http://localhost:8000/docs`.

## Intended stack

- Next.js (App Router) + React + TypeScript
- TanStack Query for API state
- A thin generated client from the FastAPI OpenAPI schema (`/openapi.json`)
