"""
Policy-enriched chunk schema per POLICY_ENGINE_PLAN Section 6.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChunkOffsets(BaseModel):
    page: int
    start_char: int
    end_char: int


class PolicyEnrichedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    tenant_id: str
    text: str
    metadata: dict = Field(default_factory=dict)
    offsets: ChunkOffsets
    element_type: str
    section_title: str | None = None


# PII policy types per POLICY_ENGINE_PLAN
PII_POLICY_REDACT = "REDACT"
PII_POLICY_FLAG = "FLAG"
PII_POLICY_BLOCK = "BLOCK"

# Presidio entity -> PRD PII code mapping
PRESIDIO_TO_PII_CODE = {
    "US_SSN": "SSN",
    "SSN": "SSN",
    "DATE_TIME": "DOB",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "PERSON": "NAME",
    "LOCATION": "ADDRESS",
    "STREET_ADDRESS": "ADDRESS",
    "CREDIT_CARD": "FINANCIAL_ACCOUNT",
    "IBAN_CODE": "FINANCIAL_ACCOUNT",
    "US_DRIVER_LICENSE": "DRIVERS_LICENSE",
    "MEDICAL_LICENSE": "MEDICAL_RECORD",
}
DEFAULT_PII_TYPES = ["SSN", "DOB", "EMAIL"]

# Classification categories per PLAN Section 3.1
CLASSIFICATION_CATEGORIES = [
    "contract", "invoice", "SOP", "policy",
    "correspondence", "legal_filing", "other",
]
