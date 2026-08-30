# IterLab reference worker

A minimal local worker that speaks the IterLab worker protocol
(`iterlab.workers.protocol`). For this phase it:

1. **registers** with the control plane and stores its worker token;
2. **advertises resources** (CPU / memory / GPU / VRAM — detected or configured);
3. **heartbeats** on the interval the controller returns;
4. **polls for tasks** (dispatch is not implemented server-side yet, so this is
   a no-op loop today).

Task execution in isolation (clone repo, run agent iteration, upload artifacts,
report a candidate) is the next milestone.

## Run

```bash
cd worker
pip install -e .

export ITERLAB_WORKER_CONTROLLER_URL=http://localhost:8000
# a user access token from POST /api/v1/auth/login is used to enroll the worker
export ITERLAB_WORKER_ENROLL_TOKEN=<access_token>
export ITERLAB_WORKER_NAME=$(hostname)

iterlab-worker
```

The worker persists its identity to `~/.iterlab/worker.json` so restarts reuse
the same registration.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `ITERLAB_WORKER_CONTROLLER_URL` | `http://localhost:8000` | Control plane base URL |
| `ITERLAB_WORKER_ENROLL_TOKEN` | — | User access token used once, to register |
| `ITERLAB_WORKER_NAME` | hostname | Display name |
| `ITERLAB_WORKER_STATE_FILE` | `~/.iterlab/worker.json` | Where the worker id + token are cached |
| `ITERLAB_WORKER_CPU` | detected | Advertised logical cores |
| `ITERLAB_WORKER_MEMORY_MB` | detected | Advertised memory |
| `ITERLAB_WORKER_GPU` | `0` | Advertised GPU count |
| `ITERLAB_WORKER_VRAM_MB` | `0` | Advertised VRAM |
| `ITERLAB_WORKER_LABELS` | — | `k=v,k=v` scheduling labels |
