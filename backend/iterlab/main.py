from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from iterlab import __version__
from iterlab.api.router import api_router
from iterlab.config import get_settings
from iterlab.core.errors import install_error_handlers
from iterlab.db.bootstrap import bootstrap_database
from iterlab.db.session import dispose_engine, get_sessionmaker
from iterlab.instance import initialize_instance
from iterlab.labs import sync_instance_labs
from iterlab.logging_config import configure_logging

logger = logging.getLogger("iterlab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.is_production)
    logger.info("starting IterLab %s (env=%s)", __version__, settings.env)
    await bootstrap_database()

    instance_dir = initialize_instance()
    if settings.instance_sync_on_startup:
        try:
            async with get_sessionmaker()() as session:
                labs, agents = await sync_instance_labs(session, instance_dir)
            if labs or agents:
                logger.info("provisioned %d instance lab(s), %d agent(s)", labs, agents)
        except Exception:  # noqa: BLE001 - a bad instance config must not block startup
            logger.exception("instance lab sync failed")

    logger.info("startup complete")
    try:
        yield
    finally:
        await dispose_engine()
        logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="IterLab",
        version=__version__,
        summary="Control plane for autonomous multi-agent experimentation",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict:
        return {"name": "IterLab", "version": __version__, "docs": "/docs"}

    return app


app = create_app()
