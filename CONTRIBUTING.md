# Contributing to IterLab

Thanks for your interest. IterLab is at the skeleton stage, so the most valuable
contributions right now are on **interfaces and architecture** rather than
features.

## Ground rules

- Discuss non-trivial changes in an issue before opening a PR.
- Keep the core free of hard dependencies on any single execution backend,
  storage backend, or LLM provider. New backends implement an existing
  abstraction (`iterlab.storage`, `iterlab.queues`, `iterlab.scheduler`,
  `iterlab.auth`).
- PostgreSQL is the source of truth. Redis holds only ephemeral state.
- The controller orchestrates; it must never execute experiment code itself.

## Development setup

```bash
cp .env.example .env            # set ITERLAB_JWT_SECRET
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

Run a local stack with `make up-bundled`.

## Before you push

```bash
make fmt
make lint
make test
```

## Commit style

Conventional-ish: `area: short imperative summary` (e.g.
`auth: rotate refresh tokens on use`). Keep PRs focused.
