"""
PostgreSQL per-tenant provisioning per STORAGE_LAYER_PLAN Section 3.
Requires superuser connection.
"""
from __future__ import annotations

import asyncpg


def _safe_identifier(tenant_id: str) -> str:
    """Sanitize tenant_id for SQL identifiers."""
    if not tenant_id.replace("_", "").isalnum():
        raise ValueError(f"Invalid tenant_id for SQL: {tenant_id}")
    return f"tenant_{tenant_id}".replace("-", "_")


async def provision_postgres_tenant(
    control_conn: asyncpg.Connection,
    tenant_id: str,
    password: str,
) -> None:
    """
    Create database and user for tenant. Per STORAGE_LAYER_PLAN 3.1.
    Must be called with superuser connection (e.g. frostbyte).
    """
    db_name = _safe_identifier(tenant_id)
    user_name = f"{db_name}_user"

    await control_conn.execute(f'CREATE DATABASE "{db_name}"')
    await control_conn.execute(
        f'CREATE USER "{user_name}" WITH ENCRYPTED PASSWORD $1',
        password,
    )
    await control_conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{user_name}"')
    await control_conn.execute(f'REVOKE CONNECT ON DATABASE "{db_name}" FROM PUBLIC')


async def deprovision_postgres_tenant(
    control_conn: asyncpg.Connection,
    tenant_id: str,
) -> None:
    """Drop database and user. Per STORAGE_LAYER_PLAN 3.3."""
    db_name = _safe_identifier(tenant_id)
    user_name = f"{db_name}_user"

    await control_conn.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = $1 AND pid <> pg_backend_pid()
        """,
        db_name,
    )
    await control_conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
    await control_conn.execute(f'DROP USER IF EXISTS "{user_name}"')
