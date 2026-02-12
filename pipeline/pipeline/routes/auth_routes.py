"""
Admin authentication: API key -> JWT.
POST /api/v1/auth/token accepts api_key, returns JWT for admin dashboard.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _get_admin_api_key() -> str | None:
    return os.getenv("FROSTBYTE_ADMIN_API_KEY") or None


def _get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "change_me_in_production_jwt_secret_32_characters")


class TokenRequest(BaseModel):
    api_key: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


@router.post("/token", response_model=TokenResponse)
async def exchange_token(req: TokenRequest):
    """
    Exchange API key for JWT. Requires FROSTBYTE_ADMIN_API_KEY to be set.
    Returns JWT with scope admin, ingest for admin dashboard access.
    """
    admin_key = _get_admin_api_key()
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AUTH_NOT_CONFIGURED", "message": "Admin API key not configured"},
        )
    if not req.api_key or req.api_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_API_KEY", "message": "Invalid API key"},
        )

    try:
        from jose import jwt
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AUTH_UNAVAILABLE", "message": "JWT support not available"},
        ) from None

    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=3600)
    payload = {
        "sub": "admin",
        "scope": "admin ingest",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(
        payload,
        _get_jwt_secret(),
        algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    )
    return TokenResponse(access_token=token, token_type="bearer", expires_in=3600)
