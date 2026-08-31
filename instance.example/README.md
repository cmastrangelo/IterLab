# Instance configuration

Copy this directory to `instance/` (git-ignored) and fill it in for your
deployment. IterLab ships **nothing** about any specific external system — all
of that wiring lives here and is never committed.

```
instance/
  .env                 # secrets: DSNs, tokens, credentials (loaded into the env)
  labs/*.yaml          # lab definitions, provisioned into the database on startup
  adapters/*.py        # optional: custom BenchmarkAdapter plugins
```

## `.env`

Plain `KEY=value` lines. Loaded into the process environment on startup
(without overwriting anything already set). Referenced from lab specs by name
only — e.g. a benchmark spec says `dsn_env: MY_LADDER_DSN`, never the DSN itself.

## `labs/*.yaml`

One lab per file. Schema: `iterlab.labs.spec.LabSpec`. On startup each is
upserted into the database as a `source: instance` lab; its benchmarks are
created `managed: true` (read-only via the API). Remove a benchmark from the
YAML and it is removed from the DB on the next startup.

See `labs/example-ladder.yaml`.

## `adapters/*.py`

Each module is imported at startup and should call
`iterlab.benchmarks.registry.register_adapter(...)`. Use this for benchmarks
that can't be expressed by a built-in adapter (e.g. running a game referee).
Built-in adapters (`sql_leaderboard`, ...) need no plugin.
