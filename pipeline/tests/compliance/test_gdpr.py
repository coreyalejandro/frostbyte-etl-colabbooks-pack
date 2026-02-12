"""
GDPR compliance test template.
Requirements: Right to erasure, data portability, consent record.
Some tests skip until DELETE /documents, /export, and metadata support exist.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_right_to_erasure(client, db, tenant_id):
    """
    GDPR: DELETE /documents/{id} must remove all document data and associated chunks.
    Skip: DELETE endpoint not yet implemented.
    """
    pytest.skip(reason="DELETE /documents/{id} endpoint not yet implemented")


@pytest.mark.asyncio
async def test_data_portability(client, tenant_id):
    """
    GDPR: GET /documents/{id}/export must return JSON with all user-provided fields.
    Skip: Export endpoint not yet implemented.
    """
    pytest.skip(reason="GET /documents/{id}/export endpoint not yet implemented")


@pytest.mark.asyncio
async def test_consent_record(client, tenant_id, db):
    """
    GDPR: Every document upload must record consent_timestamp in metadata.
    Skip: Intake does not yet accept custom_metadata per file.
    """
    pytest.skip(reason="custom_metadata with consent_timestamp not yet supported in intake")
