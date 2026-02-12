# Enhancement #7 – SSO/SAML/OIDC Integration

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing SSO (Single Sign-On) integration for the Frostbyte ETL pipeline. The system must support OIDC (OpenID Connect) as the primary protocol. All decisions about provider, endpoints, and user attribute mapping are defined in the PRD. No decisions are left open.

[OBJECTIVE]
Generate the FastAPI integration with Auth0 as the identity provider. Include login redirect, callback, JWT validation, and protected routes. Also provide environment variable configuration and testing instructions.

[STYLE]
Imperative, production-ready. Provide each file content in a code block with its full relative path. No commentary.

[AUDIENCE]
Backend developer. Execute the steps exactly as written.
```

---

## Zero-Shot Prompt

*Concatenated with the PRD and Implementation Plan below – feed this entire document to the implementation LLM.*

---

## Production Requirements Document (PRD) – SSO/SAML/OIDC Integration

### 1. Identity Provider

- **Provider**: Auth0 (can be replaced by any OIDC-compliant provider with same configuration).
- **Tenant**: `frostbyte-{env}.auth0.com`
- **Application Type**: Regular Web Application
- **Token Signature Algorithm**: RS256

### 2. Environment Variables

```
OIDC_DISCOVERY_URL=https://frostbyte-dev.auth0.com/.well-known/openid-configuration
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_client_secret
OIDC_SCOPE=openid profile email
OIDC_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET_KEY=generate_a_random_string_at_least_32_chars
```

### 3. Authentication Flow

- User visits `/auth/login` → redirect to Auth0.
- Auth0 redirects to `/auth/callback` with `code`.
- Exchange code for tokens, validate ID token, create session.
- Session stored in signed cookie (HTTP-only, Secure, SameSite=Lax).
- Protected endpoints require valid session; return 401 otherwise.

### 4. User Attribute Mapping

- `sub` → `user_id`
- `email` → `email`
- `name` → `full_name`
- `tenant_id` (custom claim) → `tenant_id` (if present)

### 5. API Protection

- All API routes under `/api/*` **must** validate the session cookie.
- Public routes: `/health`, `/auth/*`, `/docs`.
- Use `fastapi.Request` to extract session from cookie via `itsdangerous` URLSafeSerializer.

### 6. Session Management

- Session duration: 24 hours.
- Refresh token rotation not implemented in this phase.

### 7. Testing

- Mock OIDC provider for unit tests: `httpx` + `pytest-httpx`.

---

## Deterministic Implementation Plan

### Step 1 – Install dependencies

```bash
pip install authlib itsdangerous httpx
```

### Step 2 – Add environment variables to `.env.example`

```
OIDC_DISCOVERY_URL=https://frostbyte-dev.auth0.com/.well-known/openid-configuration
OIDC_CLIENT_ID=changeme
OIDC_CLIENT_SECRET=changeme
OIDC_SCOPE=openid profile email
OIDC_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET_KEY=generate_me_a_secure_random_key
```

### Step 3 – Create OIDC client and session utilities

**File**: `app/auth/oidc.py`

```python
from authlib.integrations.starlette_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from starlette.config import Config
from app.config import settings

config = Config(environ=settings.dict())
oauth = OAuth(config)
oauth.register(
    name='frostbyte-oidc',
    server_metadata_url=settings.OIDC_DISCOVERY_URL,
    client_id=settings.OIDC_CLIENT_ID,
    client_secret=settings.OIDC_CLIENT_SECRET,
    client_kwargs={'scope': settings.OIDC_SCOPE}
)
```

**File**: `app/auth/session.py`

```python
from itsdangerous import URLSafeSerializer, BadSignature
from fastapi import Request, HTTPException
from app.config import settings

serializer = URLSafeSerializer(settings.SESSION_SECRET_KEY)

def create_session_token(data: dict) -> str:
    return serializer.dumps(data)

def verify_session_token(request: Request) -> dict:
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        data = serializer.loads(session_cookie)
        return data
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")
```

### Step 4 – Create authentication endpoints

**File**: `app/api/endpoints/auth.py`

```python
from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuthError
from app.auth.oidc import oauth
from app.auth.session import create_session_token

router = APIRouter(prefix="/auth", tags=["auth"])

@router.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.frostbyte_oidc.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, response: Response):
    try:
        token = await oauth.frostbyte_oidc.authorize_access_token(request)
    except OAuthError as error:
        return {"error": error.error}
    user = token.get('userinfo')
    if not user:
        user = await oauth.frostbyte_oidc.parse_id_token(request, token)
    # Create session
    session_data = {
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "full_name": user.get("name"),
        "tenant_id": user.get("tenant_id")  # custom claim if present
    }
    session_token = create_session_token(session_data)
    response = RedirectResponse(url="/")
    response.set_cookie(
        key="session",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400
    )
    return response

@router.get("/logout")
async def logout(response: Response):
    response.delete_cookie("session")
    return {"status": "logged out"}

@router.get("/me")
async def get_current_user(request: Request):
    from app.auth.session import verify_session_token
    user = verify_session_token(request)
    return user
```

### Step 5 – Create dependency for protected routes

**File**: `app/auth/dependencies.py`

```python
from fastapi import Request, Depends, HTTPException
from app.auth.session import verify_session_token

def require_auth(request: Request):
    user = verify_session_token(request)
    return user
```

### Step 6 – Protect API routes

In `app/api/endpoints/__init__.py` or each router, add:

```python
from app.auth.dependencies import require_auth
from fastapi import Depends

@router.get("/protected-example")
async def example(user: dict = Depends(require_auth)):
    return {"user": user}
```

### Step 7 – Add OIDC configuration to settings

**File**: `app/config.py` add:

```python
class Settings(BaseSettings):
    # ... existing settings ...
    OIDC_DISCOVERY_URL: str = "https://frostbyte-dev.auth0.com/.well-known/openid-configuration"
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_SCOPE: str = "openid profile email"
    OIDC_REDIRECT_URI: str = "http://localhost:8000/auth/callback"
    SESSION_SECRET_KEY: str = ""
```

### Step 8 – Create test for OIDC flow

**File**: `tests/test_auth.py`

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_login_redirect():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/auth/login")
        assert response.status_code == 307
        assert "auth0.com/authorize" in response.headers["location"]
```

### Step 9 – Commit

```bash
git add app/auth app/api/endpoints/auth.py app/config.py
git add tests/test_auth.py
git commit -m "feat(auth): add OIDC SSO integration with Auth0"
```
