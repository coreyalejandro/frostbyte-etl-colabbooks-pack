"""
Storage layer provisioning per docs/STORAGE_LAYER_PLAN.md.
"""
from .provisioner import (
    ProvisioningError,
    provision_tenant_storage,
    verify_tenant_access,
    get_collection_name,
)

__all__ = [
    "ProvisioningError",
    "provision_tenant_storage",
    "verify_tenant_access",
    "get_collection_name",
]
