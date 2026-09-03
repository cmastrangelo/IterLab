# Immutable prompt versions

`prompts/<lab-slug>/<prompt-slug>/v<N>.md` — one file per version.

**Rules enforced at startup:**
- a version already registered in the database must be byte-identical to its
  file. Edit it and startup logs a loud error (or fails, with
  `ITERLAB_PROMPT_DRIFT_FATAL=1`) — it will NOT silently make a new version.
- new wording = a new `v<N+1>.md` file. Never edit an existing one.

**Switching versions** is the only movable knob — set it in the lab yaml:

```yaml
prompts:
  active:
    build: 1      # <prompt-slug>: <version>
```

Bump the integer to switch; old versions and their collected stats stay intact.
Revert by setting it back — no prompt text is touched.

A step handler gets the active text via `ctx.prompt("<slug>")`.
