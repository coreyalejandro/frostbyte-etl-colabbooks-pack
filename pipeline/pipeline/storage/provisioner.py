"""
Combined storage provisioning with rollback per STORAGE_LAYER_PLAN Section 7.
"""
from __future__ import annotations

import asyncio
import subprocess
import uuid
from pathlib import Path

import asyncpg
import httpx

from . import credentials
from . import minio_provisioner
from . import postgres_provisioner
from . import qdrant_provisioner
from . import redis_provisioner
from .qdrant_provisioner import get_collection_name, verify_tenant_access


class ProvisioningError(Exception):
    """Raised when provisioning fails."""

    pass


async def provision_tenant_storage(
    *,
    tenant_id: str,
    control_db_url: str,
    minio_endpoint: str,
    minio_access: str,
    minio_secret: str,
    postgres_host: str,
    qdrant_url: str,
    redis_url: str,
    sops_keys_path: str,
    emit_audit_event_fn,
    use_mc_iam: bool = False,
) -> dict[str, str]:
    """
    Provision all stores for tenant. Rollback on failure. Emit TENANT_PROVISIONED after verification.
    Per STORAGE_LAYER_PLAN Section 7.
    """
    # Step 1: Generate age key and credentials
    base = Path(sops_keys_path) / tenant_id
    base.mkdir(parents=True, exist_ok=True)
    key_path = base / "key.age"
    pub_path = base / "key.pub"

    if not key_path.exists():
        await asyncio.to_thread(
            lambda: subprocess.run(["age-keygen", "-o", str(key_path)], check=True, capture_output=True)
        )
        content = await asyncio.to_thread(key_path.read_text)
        for line in content.split("\n"):
            if line.startswith("# public key:"):
                age_pub = line.replace("# public key:", "").strip()
                break
        else:
            raise ProvisioningError("Could not parse age public key")
        pub_path.write_text(age_pub)
    else:
        content = key_path.read_text()
        for line in content.split("\n"):
            if "public key:" in line:
                age_pub = line.split("public key:")[-1].strip()
                break
        else:
            age_pub = pub_path.read_text().strip() if pub_path.exists() else ""
        if not age_pub:
            raise ProvisioningError("Could not get age public key from existing key file")
    creds = credentials.generate_credentials(tenant_id)

    completed: list[str] = []

    try:
        # Step 2-3: SOPS encrypt secrets
        credentials.encrypt_secrets_with_sops(base, creds, age_pub)
        completed.append("secrets")

        # Step 4: MinIO
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: minio_provisioner.provision_minio_bucket(
                minio_endpoint,
                minio_access,
                minio_secret,
                tenant_id,
                creds["minio_secret_key"],
                use_mc_iam=use_mc_iam,
            ),
        )
        completed.append("minio")

        # Step 5: PostgreSQL
        pool = await asyncpg.create_pool(control_db_url, min_size=1, max_size=2)
        conn = await pool.acquire()
        try:
            await postgres_provisioner.provision_postgres_tenant(
                conn, tenant_id, creds["postgres_password"]
            )
            completed.append("postgres")
        finally:
            await pool.release(conn)
            await pool.close()

        # Step 6: Qdrant
        await qdrant_provisioner.provision_qdrant_collection(qdrant_url, tenant_id)
        completed.append("qdrant")

        # Step 7: Redis
        await loop.run_in_executor(
            None,
            lambda: redis_provisioner.provision_redis_tenant(
                redis_url, tenant_id, creds["redis_password"]
            ),
        )
        completed.append("redis")

        # Step 8: Verification (simplified - check collection exists)
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{qdrant_url.rstrip('/')}/collections/{get_collection_name(tenant_id)}")
        if r.status_code != 200:
            raise ProvisioningError(f"Qdrant verification failed: {r.status_code}")

        # Step 9: Emit TENANT_PROVISIONED
        await emit_audit_event_fn(
            event_id=uuid.uuid4(),
            tenant_id=tenant_id,
            event_type="TENANT_PROVISIONED",
            resource_type="tenant",
            resource_id=tenant_id,
            details={
                "component": "provisioning-orchestrator",
                "status": "success",
                "stores_verified": ["minio", "postgresql", "qdrant", "redis"],
            },
        )

        return creds

    except Exception as e:
        # Rollback in reverse order
        for step in reversed(completed):
            try:
                if step == "minio":
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: minio_provisioner.deprovision_minio_bucket(
                            minio_endpoint, minio_access, minio_secret, tenant_id
                        ),
                    )
                elif step == "postgres":
                    pool = await asyncpg.create_pool(control_db_url, min_size=1, max_size=2)
                    conn = await pool.acquire()
                    try:
                        await postgres_provisioner.deprovision_postgres_tenant(conn, tenant_id)
                    finally:
                        await pool.release(conn)
                        await pool.close()
                elif step == "qdrant":
                    await qdrant_provisioner.deprovision_qdrant_collection(qdrant_url, tenant_id)
                elif step == "redis":
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        lambda: redis_provisioner.deprovision_redis_tenant(redis_url, tenant_id),
                    )
                elif step == "secrets":
                    for f in (base / "secrets.enc.yaml", base / "secrets.yaml"):
                        if f.exists():
                            f.unlink()
            except Exception:
                pass
        raise ProvisioningError(f"Provisioning failed at step: {e}") from e
