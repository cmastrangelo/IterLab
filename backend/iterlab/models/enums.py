from __future__ import annotations

import enum


class RunStatus(enum.StrEnum):
    pending = "pending"
    scheduled = "scheduled"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class TaskStatus(enum.StrEnum):
    queued = "queued"
    assigned = "assigned"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    lost = "lost"


class TaskKind(enum.StrEnum):
    iterate = "iterate"          # run one agent iteration -> candidate
    benchmark = "benchmark"      # evaluate a candidate
    setup = "setup"             # clone / prepare repo


class WorkerStatus(enum.StrEnum):
    online = "online"
    idle = "idle"
    busy = "busy"
    offline = "offline"
    draining = "draining"


class CandidateStatus(enum.StrEnum):
    proposed = "proposed"
    evaluated = "evaluated"
    promoted = "promoted"
    rejected = "rejected"


class ArtifactKind(enum.StrEnum):
    diff = "diff"
    patch = "patch"
    log = "log"
    report = "report"
    build = "build"
    dataset = "dataset"
    other = "other"
