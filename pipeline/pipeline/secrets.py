"""
Per-tenant secrets decryption (SOPS + age).
Reference: docs/FOUNDATION_LAYER_PLAN.md Section 2.3, TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


class SecretsError(Exception):
    """Raised when tenant secrets cannot be decrypted or are not configured."""

    pass


def decrypt_tenant_secrets(tenant_id: str, sops_keys_path: str) -> dict[str, str]:
    """
    Decrypt tenant secrets from SOPS-encrypted YAML.
    Requires SOPS_AGE_KEY_FILE=.secrets/tenants/{tenant_id}/key.age and sops CLI.
    Never log the returned dict.
    """
    base = Path(sops_keys_path) / tenant_id
    key_file = base / "key.age"
    secrets_file = base / "secrets.enc.yaml"

    if not key_file.exists():
        raise SecretsError(
            f"Tenant key not found: {key_file}. "
            "Provision tenant secrets per TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6."
        )
    if not secrets_file.exists():
        raise SecretsError(
            f"Tenant secrets file not found: {secrets_file}. "
            "Provision tenant secrets per TENANT_ISOLATION_STORAGE_ENCRYPTION Section 6."
        )

    env = os.environ.copy()
    env["SOPS_AGE_KEY_FILE"] = str(key_file.resolve())

    try:
        result = subprocess.run(
            ["sops", "--decrypt", str(secrets_file)],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
    except FileNotFoundError:
        raise SecretsError(
            "sops CLI not found. Install sops (e.g., brew install sops) for tenant secrets."
        )

    if result.returncode != 0:
        raise SecretsError(
            f"SOPS decryption failed: {result.stderr or result.stdout or 'unknown error'}"
        )

    # Parse simple YAML (key: value) for the expected structure
    out: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if ":" in line and not line.strip().startswith("#"):
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip('"').strip("'")
    return out
