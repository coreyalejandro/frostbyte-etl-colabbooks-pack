"""
Platform configuration loader.
Reference: docs/architecture/FOUNDATION_LAYER_PLAN.md Section 2.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PlatformConfig:
    """Platform-level configuration from environment variables."""

    mode: Literal["online", "offline"]
    control_db_url: str
    minio_endpoint: str
    postgres_host: str
    qdrant_url: str
    redis_url: str
    sops_keys_path: str
    embedding_endpoint: str | None
    audit_db_url: str | None

    @classmethod
    def from_env(cls) -> PlatformConfig:
        """Load and validate configuration from environment variables."""
        mode = os.getenv("FROSTBYTE_MODE", "offline").lower()
        if mode not in ("online", "offline"):
            raise ValueError(f"FROSTBYTE_MODE must be 'online' or 'offline', got {mode!r}")

        control_db_url = os.getenv(
            "FROSTBYTE_CONTROL_DB_URL",
            os.getenv(
                "POSTGRES_URL",
                "postgresql://frostbyte:frostbyte@localhost:5432/frostbyte",
            ).replace("+asyncpg", ""),
        )
        if not control_db_url:
            raise ValueError("FROSTBYTE_CONTROL_DB_URL or POSTGRES_URL is required")

        minio_endpoint = os.getenv("FROSTBYTE_MINIO_ENDPOINT", "http://localhost:9000")
        postgres_host = os.getenv("FROSTBYTE_POSTGRES_HOST", "localhost")
        qdrant_url = os.getenv("FROSTBYTE_QDRANT_URL", "http://localhost:6333")
        redis_url = os.getenv("FROSTBYTE_REDIS_URL", "redis://localhost:6379")
        sops_keys_path = os.getenv("FROSTBYTE_SOPS_KEYS_PATH", ".secrets/tenants")
        audit_db_url = os.getenv("FROSTBYTE_AUDIT_DB_URL")

        embedding_endpoint: str | None = None
        if mode == "online":
            embedding_endpoint = os.getenv("FROSTBYTE_EMBEDDING_ENDPOINT")
            if not embedding_endpoint:
                raise ValueError(
                    "FROSTBYTE_EMBEDDING_ENDPOINT is required when FROSTBYTE_MODE=online"
                )

        return cls(
            mode=mode,
            control_db_url=control_db_url,
            minio_endpoint=minio_endpoint,
            postgres_host=postgres_host,
            qdrant_url=qdrant_url,
            redis_url=redis_url,
            sops_keys_path=sops_keys_path,
            embedding_endpoint=embedding_endpoint,
            audit_db_url=audit_db_url or control_db_url,
        )
