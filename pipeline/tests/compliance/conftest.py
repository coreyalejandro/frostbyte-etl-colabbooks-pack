"""
Shared fixtures for compliance tests.
Tests run against pipeline FastAPI app and test PostgreSQL when available.
"""
from __future__ import annotations

import os

import pytest

try:
    import httpx
    from httpx import ASGITransport
except ImportError:
    httpx = None


@pytest.fixture
def tenant_id() -> str:
    """Default tenant for compliance tests."""
    return "default"


@pytest.fixture
async def client():
    """Async HTTP client for the pipeline FastAPI app. Runs app lifespan so DB is init'd."""
    if httpx is None:
        pytest.skip("httpx not installed")
    from pipeline.main import app
    # Run lifespan so init_db is called (ASGITransport does not run lifespan automatically)
    lifespan_ctx = app.router.lifespan_context(app)
    async with lifespan_ctx:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def db():
    """
    Async PostgreSQL connection for control-plane DB.
    Skips if FROSTBYTE_CONTROL_DB_URL not set or connection fails.
    """
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")
    url = os.getenv("FROSTBYTE_CONTROL_DB_URL", "postgresql://frostbyte:frostbyte@127.0.0.1:5433/frostbyte")
    try:
        conn = await asyncpg.connect(url)
        yield conn
        await conn.close()
    except Exception:
        pytest.skip("Cannot connect to control-plane database (start Docker and run migrations)")
