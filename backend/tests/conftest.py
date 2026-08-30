from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

# Configure the environment *before* importing anything from iterlab: settings,
# engine, and sessionmaker are all cached at import time.
_TMP = Path(tempfile.mkdtemp(prefix="iterlab-test-"))
os.environ.setdefault("ITERLAB_DATABASE_URL", f"sqlite+aiosqlite:///{_TMP / 'test.db'}")
os.environ.setdefault("ITERLAB_REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("ITERLAB_JWT_SECRET", "test-secret-not-for-production-0123456789abcdef")
os.environ.setdefault("ITERLAB_ENV", "test")
os.environ.setdefault("ITERLAB_STORAGE_PATH", str(_TMP / "artifacts"))
os.environ.setdefault("ITERLAB_ACCESS_TOKEN_TTL", "60")

from httpx import ASGITransport, AsyncClient  # noqa: E402

from iterlab.db.base import Base  # noqa: E402
from iterlab.db.session import get_engine  # noqa: E402
from iterlab.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> AsyncIterator[None]:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    engine = get_engine()
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test/api/v1") as c:
        yield c
