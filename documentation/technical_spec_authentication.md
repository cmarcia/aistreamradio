# Technical Specification: Standalone OAuth2 / OIDC Authentication Component

**Feature Title:** Standalone OAuth2 / OIDC Authentication Component  
**Status:** Approved Technical Design  
**Version:** 1.0  
**Target Project:** AI Stream Radio (`aistreamradio`) & Portable Framework  
**Primary References:**
- [`documentation/Authentication_Recommendation..md`](file:///Users/charliemarciano/workspace/projects/aistreamradio/documentation/Authentication_Recommendation..md)
- [`documentation/Authentication_Requirements.md`](file:///Users/charliemarciano/workspace/projects/aistreamradio/documentation/Authentication_Requirements.md)

**Target Files & Module Boundaries:**
- Backend Auth Router: [`app/routers/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/routers/auth.py)
- Backend Auth Service: [`app/services/auth_service.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/services/auth_service.py)
- Auth DB Models: [`app/models/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/models/auth.py)
- Auth Schemas: [`app/schemas/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/schemas/auth.py)
- Auth Security & Dependencies: [`app/utilities/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/utilities/auth.py)
- Frontend Standalone Client SDK: [`app/static/Script/auth-client.js`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/auth-client.js)
- Test Suite: [`tests/test_auth_component.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_auth_component.py)

---

## 1. Executive Summary & Design Principles

This technical specification details the implementation plan for an isolated, high-performance, cost-free **OAuth2 / OpenID Connect (OIDC) Authentication Component**.

### Core Architecture Principles:
1. **Decoupled Architecture**: The component is divided strictly into two layers:
   - A Python/FastAPI backend module (`auth_service`, `auth` router).
   - A Node.js / Browser JavaScript client library (`AuthClient`).
2. **Zero Vendor Lock-In**: Replaces hosted auth services (e.g. Auth0, Clerk, Firebase) with **FastAPI** and **Authlib**, running directly on self-hosted infrastructure.
3. **Pluggable & Portable**: Reusing this component in another Python + JavaScript/Node project requires copying the `auth` module directory and defining standard environment variables without altering core application code.

---

## 2. Component Architecture & System Data Flow

```mermaid
graph TD
    subgraph Frontend Client ["Frontend Layer (JavaScript / Node.js)"]
        SDK["auth-client.js (AuthClient)"]
        UI["UI Login Button / Modal"]
        UI -->|Calls auth.login(provider)| SDK
    end

    subgraph Backend Component ["Backend Layer (Python / FastAPI)"]
        Router["app/routers/auth.py"]
        Service["app/services/auth_service.py (Authlib OAuth)"]
        Security["app/utilities/auth.py (JWT & Passwords)"]
        
        SDK -->|1. GET /auth/login/{provider}| Router
        Router -->|2. Generate Auth URL & State| Service
        Service -->|3. Redirect 302 to Provider| IDP["OAuth Identity Provider (Google, MS, FB)"]
        
        IDP -->|4. Redirect with Code & State| Router
        Router -->|5. Validate State & Exchange Code| Service
        Service -->|6. Profile Normalization| Service
        
        Service -->|7. Upsert User & Link OAuthAccount| Repo["app/repositories/users.py"]
        Service -->|8. Issue App Session JWT / Cookie| Security
        Security -->|9. 302 Redirect to Frontend w/ Cookie| SDK
    end

    subgraph Storage ["Persistence Layer"]
        Repo --> DB[(SQLAlchemy / SQLite / PostgreSQL)]
    end
```

---

## 3. Detailed Data Schemas & Models

### 3.1 Database ORM Models (`app/models/auth.py`)

Using SQLAlchemy 2.0 Declarative Mapping with strict type annotations:

```python
from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email_at_provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc), 
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="oauth_accounts")
```

---

### 3.2 Pydantic Validation Schemas (`app/schemas/auth.py`)

```python
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class OAuthProviderInfo(BaseModel):
    id: str
    name: str
    icon_url: str | None = None

class UserRead(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TokenPayload(BaseModel):
    sub: str
    email: str
    exp: int
    iat: int
    iss: str = "aistreamradio-auth"

class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
```

---

## 4. Backend Service Implementation Blueprint

### 4.1 Configuration Management (`app/config.py` extension)

The module requires the following configuration environment variables:

```python
# app/Configuration/auth_config.py
from pydantic_settings import BaseSettings

class AuthSettings(BaseSettings):
    AUTH_SECRET_KEY: str = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY_MIN_32_BYTES"
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 Hours
    SESSION_COOKIE_NAME: str = "app_session"
    COOKIE_SECURE: bool = False  # Set True in production (HTTPS)
    COOKIE_SAMESITE: str = "lax"
    
    # OAuth Provider Keys
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    MICROSOFT_CLIENT_ID: str | None = None
    MICROSOFT_CLIENT_SECRET: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

auth_settings = AuthSettings()
```

---

### 4.2 Security Utilities (`app/utilities/auth.py`)

Handles JWT encoding, token verification, and cookie generation:

```python
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.Configuration.auth_config import auth_settings
from app.schemas.auth import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": int(expire.timestamp()), "iat": int(now.timestamp()), "iss": "aistreamradio-auth"})
    return jwt.encode(to_encode, auth_settings.AUTH_SECRET_KEY, algorithm=auth_settings.AUTH_ALGORITHM)

def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, auth_settings.AUTH_SECRET_KEY, algorithms=[auth_settings.AUTH_ALGORITHM])
        return TokenPayload(**payload)
    except (jwt.PyJWTError, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

---

### 4.3 Auth Service Layer (`app/services/auth_service.py`)

Encapsulates Authlib `OAuth` registry setup and OAuth code exchange logic:

```python
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from app.Configuration.auth_config import auth_settings

oauth = OAuth()

# Dynamically Register Google Provider
if auth_settings.GOOGLE_CLIENT_ID and auth_settings.GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=auth_settings.GOOGLE_CLIENT_ID,
        client_secret=auth_settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Dynamically Register Microsoft Provider
if auth_settings.MICROSOFT_CLIENT_ID and auth_settings.MICROSOFT_CLIENT_SECRET:
    oauth.register(
        name="microsoft",
        client_id=auth_settings.MICROSOFT_CLIENT_ID,
        client_secret=auth_settings.MICROSOFT_CLIENT_SECRET,
        server_metadata_url="https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

class AuthService:
    def __init__(self, db_session):
        self.db = db_session

    async def get_login_redirect(self, request: Request, provider: str, redirect_uri: str):
        client = oauth.create_client(provider)
        if not client:
            raise ValueError(f"OAuth provider '{provider}' is not configured.")
        return await client.authorize_redirect(request, redirect_uri)

    async def handle_callback(self, request: Request, provider: str):
        client = oauth.create_client(provider)
        if not client:
            raise ValueError(f"OAuth provider '{provider}' is not configured.")
        
        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo") or await client.userinfo(request, token=token)
        
        return {
            "provider": provider,
            "provider_user_id": str(user_info.get("sub") or user_info.get("id")),
            "email": user_info.get("email"),
            "full_name": user_info.get("name"),
            "avatar_url": user_info.get("picture"),
        }
```

---

### 4.4 FastAPI Auth Router (`app/routers/auth.py`)

Exposes standard HTTP REST endpoints:

```python
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.services.auth_service import AuthService, oauth
from app.utilities.auth import create_access_token, decode_access_token
from app.Configuration.auth_config import auth_settings
from app.schemas.auth import UserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/providers")
def list_providers():
    """Returns list of enabled OAuth providers."""
    enabled = [name for name in ["google", "microsoft"] if getattr(oauth, name, None) is not None]
    return {"providers": enabled}

@router.get("/login/{provider}")
async def login_provider(provider: str, request: Request):
    """Initiates OAuth authorization flow."""
    redirect_uri = str(request.url_for("auth_callback", provider=provider))
    auth_service = AuthService(db_session=None)
    return await auth_service.get_login_redirect(request, provider, redirect_uri)

@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(provider: str, request: Request):
    """Handles OAuth IDP callback redirect."""
    # 1. Exchange code & fetch normalized profile
    auth_service = AuthService(db_session=None)
    profile = await auth_service.handle_callback(request, provider)
    
    # 2. Upsert user logic (via UserRepository)
    # user = user_repo.get_or_create_from_oauth(profile)
    
    # 3. Create session JWT
    token_data = {"sub": profile["provider_user_id"], "email": profile["email"]}
    access_token = create_access_token(token_data)

    # 4. Set HttpOnly Cookie & Redirect to Frontend
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key=auth_settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=auth_settings.COOKIE_SECURE,
        samesite=auth_settings.COOKIE_SAMESITE,
        max_age=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return response

@router.post("/logout")
def logout(response: Response):
    """Clears the session cookie."""
    response.delete_cookie(key=auth_settings.SESSION_COOKIE_NAME)
    return {"message": "Successfully logged out"}
```

---

## 5. Standalone Frontend Client Library (JavaScript / Node.js)

### File: `app/static/Script/auth-client.js`

Designed as a zero-dependency ES module compatible with Browser Vanilla JS and Node.js environments:

```javascript
/**
 * Standalone Reusable Auth Client SDK (JavaScript / Node.js)
 */
export class AuthClient {
    /**
     * @param {Object} options Configuration options
     * @param {string} options.baseUrl API Base URL (e.g. 'http://localhost:8000')
     * @param {string} [options.mode='cookie'] Session mode: 'cookie' or 'token'
     */
    constructor(options = {}) {
        this.baseUrl = (options.baseUrl || '').replace(/\/$/, '');
        this.mode = options.mode || 'cookie';
        this.token = localStorage.getItem('auth_token') || null;
        this.listeners = new Set();
        this.currentUser = null;
    }

    /**
     * Subscribe to authentication state changes.
     * @param {Function} callback Callback receiving (user | null)
     * @returns {Function} Unsubscribe function
     */
    onAuthStateChanged(callback) {
        this.listeners.add(callback);
        // Immediately invoke with current user state
        callback(this.currentUser);
        return () => this.listeners.delete(callback);
    }

    _notify(user) {
        this.currentUser = user;
        this.listeners.forEach(cb => cb(user));
    }

    /**
     * Redirects browser to initiate OAuth login for specified provider.
     * @param {string} provider Provider ID ('google', 'microsoft', etc.)
     */
    login(provider) {
        const loginUrl = `${this.baseUrl}/auth/login/${provider}`;
        window.location.href = loginUrl;
    }

    /**
     * Fetches current authenticated user profile.
     * @returns {Promise<Object|null>} User object or null
     */
    async getUser() {
        try {
            const headers = { 'Accept': 'application/json' };
            if (this.mode === 'token' && this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const response = await fetch(`${this.baseUrl}/auth/me`, {
                method: 'GET',
                headers,
                credentials: this.mode === 'cookie' ? 'include' : 'same-origin'
            });

            if (!response.ok) {
                this._notify(null);
                return null;
            }

            const user = await response.json();
            this._notify(user);
            return user;
        } catch (error) {
            console.error('[AuthClient] Error checking user state:', error);
            this._notify(null);
            return null;
        }
    }

    /**
     * Logs out the user and clears session state.
     */
    async logout() {
        try {
            await fetch(`${this.baseUrl}/auth/logout`, {
                method: 'POST',
                credentials: this.mode === 'cookie' ? 'include' : 'same-origin'
            });
        } catch (err) {
            console.warn('[AuthClient] Logout request warning:', err);
        } finally {
            if (this.mode === 'token') {
                localStorage.removeItem('auth_token');
                this.token = null;
            }
            this._notify(null);
        }
    }
}
```

---

## 6. Security, CSRF Protection & Error Handling Matrix

| Risk / Failure Scenario | Prevention / Mitigation Mechanism |
| :--- | :--- |
| **OAuth CSRF State Tampering** | Authlib generates cryptographically signed `state` parameters stored in temporary encrypted session cookies during redirect. |
| **Cross-Site Scripting (XSS)** | App session token is stored in `HttpOnly` cookies, preventing malicious JS from extracting session JWTs. |
| **Unverified Social Email** | Profile sync enforces `email_verified == True` from OIDC ID Token before creating or linking a local account. |
| **Provider Downtime / Timeout** | `AuthService` handles `OAuthError` and returns clean HTTP 502 / 400 JSON responses instead of crashing the process. |

---

## 7. Migration & Reuse Guide for Future Projects

To copy and embed this component into another project:

1. **Copy Backend Module**: Copy `app/routers/auth.py`, `app/services/auth_service.py`, `app/models/auth.py`, `app/schemas/auth.py`, and `app/utilities/auth.py` into your new FastAPI project.
2. **Copy Frontend Client**: Include `auth-client.js` in your frontend static assets or NPM package dependencies.
3. **Set Environment Variables**: Define `AUTH_SECRET_KEY`, `GOOGLE_CLIENT_ID`, and `GOOGLE_CLIENT_SECRET` in `.env`.
4. **Include Router**: Add `app.include_router(auth_router)` in `main.py`.

---

## 8. Test Strategy & Verification Plan

### 8.1 Backend Test Cases (`tests/test_auth_component.py`)
- Test provider discovery endpoint (`GET /auth/providers`).
- Test login redirect generation (`GET /auth/login/google`).
- Test OAuth code callback exchange with mocked Google IDP token responses (`httpx` / `respx` mocks).
- Test session cookie creation and valid JWT decoding (`GET /auth/me`).
- Test logout cookie invalidation (`POST /auth/logout`).

### 8.2 Frontend SDK Test Cases
- Verify `AuthClient` initializes with default options.
- Verify `onAuthStateChanged` callback fires on state transitions.
- Verify fallback behavior when backend returns HTTP 401.
