"""
Credential generation and SOPS encryption per STORAGE_LAYER_PLAN Section 6.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import secrets


def generate_credentials(tenant_id: str) -> dict[str, str]:
    """Generate all credentials for a tenant. Per STORAGE_LAYER_PLAN 6.2."""
    return {
        "minio_access_key": f"tenant-{tenant_id}-access",
        "minio_secret_key": secrets.token_urlsafe(32),
        "postgres_password": secrets.token_urlsafe(32),
        "qdrant_api_key": secrets.token_urlsafe(32),
        "redis_password": secrets.token_urlsafe(32),
        "tenant_api_key": secrets.token_urlsafe(32),
    }


def encrypt_secrets_with_sops(
    base_path: Path,
    creds: dict[str, str],
    age_public_key: str,
) -> None:
    """Write secrets YAML and encrypt with SOPS. Per STORAGE_LAYER_PLAN 6.4."""
    base_path.mkdir(parents=True, exist_ok=True)
    plain_path = base_path / "secrets.yaml"
    enc_path = base_path / "secrets.enc.yaml"

    lines = [f"{k}: \"{v}\"" for k, v in creds.items()]
    plain_path.write_text("\n".join(lines) + "\n")

    result = subprocess.run(
        ["sops", "--age", age_public_key, "--encrypt", str(plain_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"SOPS encrypt failed: {result.stderr or result.stdout}")

    enc_path.write_text(result.stdout)
    plain_path.unlink()
