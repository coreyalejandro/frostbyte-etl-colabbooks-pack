"""
Storage layer unit tests. Verifies provisioning logic without Docker.
"""
from __future__ import annotations

import pytest

from pipeline.storage.qdrant_provisioner import (
    get_collection_name,
    verify_tenant_access,
)


class TestQdrantProvisioner:
    def test_get_collection_name(self) -> None:
        assert get_collection_name("abc") == "tenant_abc"
        assert get_collection_name("tenant-1") == "tenant_tenant-1"

    def test_verify_tenant_access_ok(self) -> None:
        verify_tenant_access("abc", "tenant_abc")

    def test_verify_tenant_access_denied(self) -> None:
        with pytest.raises(PermissionError, match="cannot access"):
            verify_tenant_access("abc", "tenant_other")
