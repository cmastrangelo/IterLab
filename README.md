# IterLab

**IterLab** is an open-source platform for orchestrating autonomous multi-agent
experimentation.

Users create **Projects / Labs**, connect an existing external code repository,
assign one or more LLM agents/models, and run **iterative experiments** in which
agents research, modify, test, and improve a solution. Each iteration produces a
**candidate** that can be benchmarked against previous candidates, creating a
persistent lineage and letting IterLab graph performance, cost, model
effectiveness, and progress over time.

> **Status:** early skeleton. This repository currently contains the
> architectural scaffold — authentication, database/schema bootstrap, the core
> data model, and the worker protocol — not the full autonomous research system.
> See [`docs/architecture.md`](docs/architecture.md) for the target design.

---

## Architecture at a glance

| Layer | Technology | Role |
| --- | --- | --- |
| Control plane / API | Python + FastAPI | Orchestrates experiments; never executes them directly |
| Web interface | TypeScript + Next.js/React | Dashboard for projects, labs, experiments, workers *(planned)* |
| Source of truth | PostgreSQL | Users, projects, labs, runs, candidates, lineage, metrics |
| Coordination | Redis | Ephemeral queues, worker heartbeats, locks |
| Artifact storage | Filesystem (pluggable) | Behind a storage abstraction; S3/MinIO later |
| Execution | Local workers | Register, heartbeat, advertise resources, run tasks in isolation |

Every external system sits behind an interface so distributed workers,
Kubernetes / ClearML / Ray backends, S3/MinIO, and additional LLM providers can
be added later without restructuring the core:

- `iterlab.auth` — `AuthProvider` (local password auth today)
- `iterlab.storage` — `ArtifactStorage` (filesystem today)
- `iterlab.queues` — `Queue` / `KeyValue` (Redis today)
- `iterlab.scheduler` — `Scheduler` (in-process today)
- `iterlab.workers.protocol` — the worker <-> controller wire contract

---

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/your-org/iterlab.git
cd iterlab
cp .env.example .env
# edit .env — at minimum set ITERLAB_JWT_SECRET
```

### 2a. Run everything, including a bundled PostgreSQL

```bash
docker compose --profile bundled-db up --build
```

This starts the web UI, API, Redis, and a PostgreSQL instance. On startup the
API creates the `iterlab` schema and all tables automatically.

- Web UI — <http://localhost:3000> (register / login / placeholder home)
- API + interactive docs — <http://localhost:8000/docs>

### 2b. Run against an existing / external PostgreSQL

Set `ITERLAB_DATABASE_URL` in `.env` to your instance and start without the
`bundled-db` profile:

```bash
# .env
ITERLAB_DATABASE_URL=postgresql+asyncpg://user:pass@db.internal:5432/mydb
ITERLAB_DB_SCHEMA=iterlab          # created if missing; keeps IterLab isolated
ITERLAB_DB_AUTO_CREATE=true        # create schema + tables on startup
```

```bash
docker compose up --build
```

IterLab confines itself to its own schema (`iterlab` by default), so it can
safely share a database with other applications.

### 3. Use it

Open <http://localhost:3000>, create an account, and you land on the (currently
placeholder) home page. Or hit the API directly:

```bash
# Register
curl -X POST localhost:8000/api/v1/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"correct-horse-battery-staple","full_name":"Me"}'

# Log in
curl -X POST localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"correct-horse-battery-staple"}'

# Current user
curl localhost:8000/api/v1/auth/me -H 'authorization: Bearer <access_token>'
```

Interactive API docs: <http://localhost:8000/docs>

---

## Local development (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# point at a running postgres + redis (see .env.example for var names)
export ITERLAB_DATABASE_URL=postgresql+asyncpg://iterlab:iterlab@localhost:5432/iterlab
export ITERLAB_REDIS_URL=redis://localhost:6379/0
export ITERLAB_JWT_SECRET=dev-only-not-secret

uvicorn iterlab.main:app --reload
pytest
```

The `worker/` package contains a reference local worker that registers with the
control plane and heartbeats. See [`worker/README.md`](worker/README.md).

---

## Repository layout

```
backend/            FastAPI control plane
  iterlab/
    api/            HTTP routes + dependencies
    auth/           AuthProvider abstraction (local password auth)
    core/           security primitives, error types
    db/             engine, session, schema/table bootstrap
    models/         SQLAlchemy models — the PostgreSQL source of truth
    queues/         Redis-backed queue / kv abstraction
    schemas/        Pydantic request/response models
    scheduler/      Scheduler abstraction (in-process today)
    services/       business logic (auth, ...)
    storage/        ArtifactStorage abstraction (filesystem today)
    workers/        worker <-> controller protocol
  tests/
  iterlab/
    benchmarks/     BenchmarkAdapter abstraction + built-in adapters
    labs/           instance lab spec + provisioning loader
    instance.py     discovery of the deployment's private instance/ config
worker/             reference local worker
web/                Next.js web interface (auth, labs, benchmarks)
instance.example/   template for the git-ignored instance/ config
docs/               architecture notes
```

---

## Configuration

All settings are read from environment variables prefixed with `ITERLAB_`
(see [`.env.example`](.env.example)). Highlights:

| Variable | Default | Purpose |
| --- | --- | --- |
| `ITERLAB_DATABASE_URL` | `postgresql+asyncpg://iterlab:iterlab@localhost:5432/iterlab` | SQLAlchemy async URL for PostgreSQL |
| `ITERLAB_DB_SCHEMA` | `iterlab` | Schema IterLab owns; created if missing |
| `ITERLAB_DB_AUTO_CREATE` | `true` | Create schema + tables on startup (dev). Use Alembic in production |
| `ITERLAB_REDIS_URL` | `redis://localhost:6379/0` | Redis for queues/coordination |
| `ITERLAB_STORAGE_BACKEND` | `filesystem` | Artifact storage backend |
| `ITERLAB_STORAGE_PATH` | `./data/artifacts` | Filesystem artifact root |
| `ITERLAB_JWT_SECRET` | — (**required**) | Signing key for access tokens |
| `ITERLAB_ACCESS_TOKEN_TTL` | `900` | Access token lifetime (seconds) |
| `ITERLAB_REFRESH_TOKEN_TTL` | `2592000` | Refresh token lifetime (seconds) |
| `ITERLAB_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |

---

## Labs & the instance directory

A **Lab** is a workspace: a connected repo, its baseline, and one or more
**benchmarks**. IterLab ships nothing about any specific repo or benchmark
backend — a deployment adds that privately under `instance/` (git-ignored):

```
instance/
  .env             # secrets: DSNs, tokens (loaded into the environment)
  labs/*.yaml       # lab definitions, provisioned into the DB on startup
  adapters/*.py     # optional custom BenchmarkAdapter plugins
```

Copy `instance.example/` to `instance/` and edit. On startup each
`labs/*.yaml` is upserted as a `source: instance` lab; its benchmarks are
created read-only. A benchmark names a **BenchmarkAdapter** (`sql_leaderboard`
is built in — a ranked leaderboard from an arbitrary SQL query) plus a `spec`
that references secrets by env-var name only, never inline.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Contributions are welcome — the
skeleton is deliberately small and the interfaces are the important part.

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).
