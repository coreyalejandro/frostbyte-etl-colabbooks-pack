"""
Verification test suite endpoint.
API-07: POST /api/v1/verification/test

MVP: deterministic mock responses keyed on testType.
TODO: Integrate with actual verification logic (gate-based analysis).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from ..auth import get_tenant_from_token

router = APIRouter(prefix="/api/v1/verification", tags=["verification"])

_MOCK_RESULTS: dict[str, dict] = {
    "red-team": {
        "score": 85,
        "details": [
            {"test": "Injection", "passed": True, "message": "No injection vulnerabilities detected."},
            {"test": "Encryption", "passed": False, "message": "TLS 1.0 detected on internal service."},
            {"test": "AuthBypass", "passed": True, "message": "Authentication cannot be bypassed."},
            {"test": "DataExfiltration", "passed": True, "message": "Exfiltration vectors blocked."},
        ],
    },
    "compliance": {
        "score": 92,
        "details": [
            {"test": "GDPR-DataMinimization", "passed": True, "message": "Only required fields collected."},
            {"test": "HIPAA-Encryption", "passed": True, "message": "PHI encrypted at rest and in transit."},
            {"test": "FedRAMP-AuditLog", "passed": True, "message": "Audit log is append-only and complete."},
            {"test": "RetentionPolicy", "passed": False, "message": "Retention policy not enforced on archived docs."},
        ],
    },
    "penetration": {
        "score": 78,
        "details": [
            {"test": "SQLInjection", "passed": True, "message": "Parameterized queries in use."},
            {"test": "XSS", "passed": True, "message": "Content-Security-Policy header present."},
            {"test": "CSRF", "passed": False, "message": "CSRF token missing on state-changing endpoints."},
            {"test": "BruteForce", "passed": True, "message": "Rate limiting active on auth endpoints."},
        ],
    },
}

VALID_TEST_TYPES = set(_MOCK_RESULTS.keys())


class VerificationTestRequest(BaseModel):
    testType: str


class VerificationDetail(BaseModel):
    test: str
    passed: bool
    message: str


class VerificationTestResponse(BaseModel):
    score: int
    details: list[VerificationDetail]


@router.post("/test", response_model=VerificationTestResponse)
async def run_verification_test(
    body: VerificationTestRequest,
    _: str | None = Depends(get_tenant_from_token),
) -> VerificationTestResponse:
    """Run a deterministic mock verification test suite by test type."""
    if body.testType not in VALID_TEST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error_code": "INVALID_TEST_TYPE",
                "message": f"testType must be one of: {', '.join(sorted(VALID_TEST_TYPES))}",
            },
        )
    result = _MOCK_RESULTS[body.testType]
    return VerificationTestResponse(
        score=result["score"],
        details=[VerificationDetail(**d) for d in result["details"]],
    )
