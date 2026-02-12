"""
JWT validation per INTAKE_GATEWAY_PLAN Section 2.1.
Bypass when FROSTBYTE_AUTH_BYPASS=true for local dev.
"""
from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    return os.getenv("JWT_SECRET", "change_me_in_production_jwt_secret_32_characters")


def _get_auth_bypass() -> bool:
    return os.getenv("FROSTBYTE_AUTH_BYPASS", "false").lower() in ("true", "1", "yes")


async def get_tenant_from_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> str | None:
    """
    Extract tenant_id from JWT. Returns None if bypass enabled and no token.
    Raises 401 if token invalid/expired, 403 if scope insufficient.
    """
    if _get_auth_bypass():
        if not credentials:
            return None  # Caller can use path tenant_id
        # Still validate if token provided
        pass

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": "Missing Bearer token"},
        )

    try:
        from jose import JWTError, jwt
        from jose.exceptions import ExpiredSignatureError

        payload = jwt.decode(
            credentials.credentials,
            _get_jwt_secret(),
            algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
        )
        tenant_id = payload.get("tenant_id") or payload.get("sub")
        scopes = payload.get("scope", "")
        if isinstance(scopes, str):
            scopes = scopes.split() if scopes else []
        if "ingest" not in scopes and "ingest" not in str(payload.get("scopes", [])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "INSUFFICIENT_PERMISSIONS", "message": "Token requires ingest scope"},
            )
        return tenant_id or None
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "TOKEN_EXPIRED", "message": "JWT has expired"},
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": str(e) or "Invalid token"},
        )


def require_tenant_or_bypass(
    path_tenant_id: str,
    token_tenant_id: str | None,
) -> str:
    """Require token tenant_id to match path, or allow when bypass + no token."""
    if _get_auth_bypass() and token_tenant_id is None:
        return path_tenant_id
    if token_tenant_id and token_tenant_id != path_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "MANIFEST_INVALID", "message": "Token tenant_id does not match path"},
        )
    if not token_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": "Valid JWT required"},
        )
    return token_tenant_id
