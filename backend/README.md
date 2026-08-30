# IterLab backend (control plane)

FastAPI application. Orchestrates experiments; it does not execute them.

```
iterlab/
  main.py         app factory, lifespan (bootstrap), middleware
  config.py       ITERLAB_* settings
  api/            routes + dependencies
  auth/           AuthProvider abstraction (local password auth)
  core/           security primitives (hashing, JWT), error types
  db/             async engine, session, schema/table bootstrap
  models/         SQLAlchemy models — the PostgreSQL source of truth
  queues/         Redis-backed Queue / KeyValue abstraction
  schemas/        Pydantic request/response models
  scheduler/      Scheduler abstraction (in-process today)
  services/       business logic
  storage/        ArtifactStorage abstraction (filesystem today)
  workers/        worker <-> controller protocol models
```

## Run

```bash
pip install -e '.[dev]'
export ITERLAB_DATABASE_URL=postgresql+asyncpg://iterlab:iterlab@localhost:5432/iterlab
export ITERLAB_REDIS_URL=redis://localhost:6379/0
export ITERLAB_JWT_SECRET=dev-only
uvicorn iterlab.main:app --reload
```

## Test

```bash
pytest
```

Tests run against SQLite (`aiosqlite`) so no PostgreSQL is needed for the unit
suite.

## Migrations

Dev uses auto-create (`ITERLAB_DB_AUTO_CREATE=true`). For production:

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```
