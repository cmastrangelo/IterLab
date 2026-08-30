# IterLab architecture

This document describes the **target** design. The current codebase implements
the parts marked _implemented_; everything else is scaffolding with an interface
in place.

## Principles

1. **PostgreSQL is the source of truth.** Every durable entity lives there.
2. **Redis is ephemeral.** Queues, heartbeats, locks, short-lived coordination.
   Losing Redis must never lose committed work.
3. **The controller orchestrates, it does not execute.** Experiment code runs
   only on workers, in isolation.
4. **Backends sit behind interfaces.** Storage, queue, scheduler, auth, and LLM
   providers are swappable without touching the core.
5. **Auth is modular.** Deployment modes (single-user, team, SSO, ...) can
   evolve behind `AuthProvider`.

## Domains

| Domain | Purpose | State |
| --- | --- | --- |
| Users / Auth | Accounts, sessions, refresh tokens, API keys | _implemented (local password)_ |
| Projects | Top-level container owned by a user/org | model _implemented_ |
| Labs | A workspace within a project: repo connection + agent roster + settings | model _implemented_ |
| Experiments / Runs | An experiment definition; a run is one execution attempt | model _implemented_ |
| Agents / Models | LLM agent configs (provider, model, params, tools) | model _implemented_ |
| Candidates / Lineage | An iteration's output; parent links form a lineage tree | model _implemented_ |
| Benchmarks | Named evaluation producing comparable scores | model _implemented_ |
| Workers | Registered executors advertising CPU/GPU/VRAM | model + protocol _implemented_ |
| Tasks | Unit of work dispatched to a worker | model _implemented_ |
| Metrics | Time-series measurements (score, cost, tokens, latency) | model _implemented_ |
| Artifacts | Blobs (diffs, logs, build outputs) behind storage abstraction | model + fs backend _implemented_ |
| Scheduler | Decides which task runs where and when | interface _implemented (in-process stub)_ |

## Request / execution flow (target)

```
User → Web → API (control plane)
                 │  creates Experiment + Run rows in PostgreSQL
                 │  enqueues Task(s) in Redis
                 ▼
            Scheduler  ── assigns ──▶  Worker (polls / receives task)
                 ▲                        │ clones repo, runs agent loop in isolation
                 │                        │ uploads artifacts via storage API
                 └── results ◀────────────┘ reports Candidate + Metrics
                 │
   API persists Candidate, Metrics, lineage edge in PostgreSQL
```

## Worker protocol

Defined in `iterlab.workers.protocol` (Pydantic models, transport-agnostic).

- `POST /api/v1/workers/register` → `{worker_id, token}`
- `POST /api/v1/workers/{id}/heartbeat` → resources + current task status
- `GET  /api/v1/workers/{id}/tasks` → next assigned task (long-poll later)
- `POST /api/v1/tasks/{id}/result` → candidate + metrics + artifact refs

Workers authenticate with a dedicated worker token, separate from user sessions.

## Extension points

| Interface | Today | Later |
| --- | --- | --- |
| `iterlab.storage.ArtifactStorage` | `FilesystemStorage` | S3, MinIO, GCS |
| `iterlab.queues.Queue` | Redis lists/streams | SQS, NATS, Kafka |
| `iterlab.scheduler.Scheduler` | in-process greedy | Ray, ClearML, Kubernetes Jobs |
| `iterlab.auth.AuthProvider` | local password | OIDC/SSO, org RBAC |
| LLM providers | (config only) | Anthropic, OpenAI, local, ... via a provider registry |

## Schema management

Dev: `ITERLAB_DB_AUTO_CREATE=true` runs `CREATE SCHEMA IF NOT EXISTS` +
`Base.metadata.create_all` on startup, scoped to `ITERLAB_DB_SCHEMA`.

Production: set `ITERLAB_DB_AUTO_CREATE=false` and run Alembic migrations
(`backend/alembic/`). IterLab only ever touches its own schema.
