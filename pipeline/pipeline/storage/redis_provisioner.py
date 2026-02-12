"""
Redis per-tenant ACL provisioning per STORAGE_LAYER_PLAN Section 5.
Requires Redis >= 6 with ACL support.
"""
from __future__ import annotations

import redis


def _acl_user(tenant_id: str) -> str:
    return f"tenant_{tenant_id}_user"


def provision_redis_tenant(
    redis_url: str,
    tenant_id: str,
    password: str,
) -> None:
    """
    Create ACL user for tenant. Per STORAGE_LAYER_PLAN 5.2.
    Key prefix: tenant:{tenant_id}:*
    """
    r = redis.from_url(redis_url)
    user = _acl_user(tenant_id)
    pattern = f"tenant:{tenant_id}:*"
    # ACL SETUSER: on >password ~pattern +@all -@dangerous
    r.execute_command("ACL", "SETUSER", user, "on", f">{password}", f"~{pattern}", "+@all", "-@dangerous")
    r.execute_command("ACL", "SAVE")
    r.close()


def deprovision_redis_tenant(redis_url: str, tenant_id: str) -> None:
    """Remove ACL user and keys. Per STORAGE_LAYER_PLAN 5.4."""
    r = redis.from_url(redis_url)
    user = _acl_user(tenant_id)
    # Delete keys
    for key in r.scan_iter(f"tenant:{tenant_id}:*"):
        r.delete(key)
    r.execute_command("ACL", "DELUSER", user)
    r.execute_command("ACL", "SAVE")
    r.close()
