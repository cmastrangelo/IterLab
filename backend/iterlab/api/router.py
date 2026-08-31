from fastapi import APIRouter

from iterlab.api.routes import (
    agents,
    auth,
    benchmarks,
    experiments,
    health,
    labs,
    projects,
    workers,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(labs.router, prefix="/labs", tags=["labs"])
api_router.include_router(experiments.lab_experiments, prefix="/labs", tags=["experiments"])
api_router.include_router(benchmarks.router, prefix="/benchmarks", tags=["benchmarks"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
api_router.include_router(experiments.candidates_router, prefix="/candidates", tags=["experiments"])
api_router.include_router(experiments.runs, prefix="/runs", tags=["experiments"])
api_router.include_router(workers.router, prefix="/workers", tags=["workers"])
