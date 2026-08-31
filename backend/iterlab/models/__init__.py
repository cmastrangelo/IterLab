"""SQLAlchemy models — the PostgreSQL source of truth.

Importing this package registers every model on ``Base.metadata`` (used by both
the startup bootstrap and Alembic autogenerate).
"""

from iterlab.models.agent import Agent
from iterlab.models.artifact import Artifact
from iterlab.models.auth_session import AuthSession
from iterlab.models.benchmark import Benchmark, BenchmarkResult
from iterlab.models.candidate import Candidate
from iterlab.models.experiment import Experiment, Run
from iterlab.models.lab import Lab, LabAgent
from iterlab.models.metric import Metric
from iterlab.models.project import Project
from iterlab.models.prompt import Prompt
from iterlab.models.run_step import RunStep
from iterlab.models.task import Task
from iterlab.models.user import User
from iterlab.models.worker import Worker

__all__ = [
    "Agent",
    "Artifact",
    "AuthSession",
    "Benchmark",
    "BenchmarkResult",
    "Candidate",
    "Experiment",
    "Lab",
    "LabAgent",
    "Metric",
    "Project",
    "Prompt",
    "Run",
    "RunStep",
    "Task",
    "User",
    "Worker",
]
