# Task Breakdown: Standalone OAuth2 / OIDC Authentication Feature

**Feature Title:** Modular Standalone OAuth2 / OIDC Authentication Component  
**Status:** Ready for Implementation Review  
**Version:** 1.0  
**Related Documents:**
- [`documentation/Authentication_Recommendation..md`](file:///Users/charliemarciano/workspace/projects/aistreamradio/documentation/Authentication_Recommendation..md)
- [`documentation/Authentication_Requirements.md`](file:///Users/charliemarciano/workspace/projects/aistreamradio/documentation/Authentication_Requirements.md)
- [`documentation/technical_spec_authentication.md`](file:///Users/charliemarciano/workspace/projects/aistreamradio/documentation/technical_spec_authentication.md)

---

## Task Summary Checklist

- [x] **Phase 1: Environment & Dependency Configuration**
  - [x] Task 1.1: Add `Authlib`, `pyjwt`, `pydantic-settings`, and `email-validator` to project dependencies (`pyproject.toml` / `uv.lock`).
  - [x] Task 1.2: Create configuration settings module [`app/Configuration/auth_config.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/Configuration/auth_config.py) and update `.env.example`.

- [x] **Phase 2: Database Schema & ORM Repositories**
  - [x] Task 2.1: Implement `User` and `OAuthAccount` SQLAlchemy ORM models in [`app/models/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/models/auth.py).
  - [x] Task 2.2: Implement Pydantic data schemas in [`app/schemas/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/schemas/auth.py).
  - [x] Task 2.3: Implement `UserRepository` in [`app/repositories/users.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/repositories/users.py) with OAuth user upsert & linking logic.
  - [x] Task 2.4: Ensure tables are automatically created on app startup in [`app/main.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/main.py).

- [x] **Phase 3: Security Core & Auth Service**
  - [x] Task 3.1: Implement JWT token creation & decoding utilities in [`app/utilities/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/utilities/auth.py).
  - [x] Task 3.2: Implement `AuthService` layer using `Authlib` in [`app/services/auth_service.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/services/auth_service.py).
  - [x] Task 3.3: Implement FastAPI `get_current_user` security dependency for protecting API routes.

- [x] **Phase 4: Backend REST API Router & Endpoints**
  - [x] Task 4.1: Create FastAPI router in [`app/routers/auth.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/routers/auth.py).
  - [x] Task 4.2: Implement `GET /auth/providers` (lists active identity providers).
  - [x] Task 4.3: Implement `GET /auth/login/{provider}` (initiates OAuth redirect).
  - [x] Task 4.4: Implement `GET /auth/callback/{provider}` (handles authorization code exchange, user creation, and session cookie setting).
  - [x] Task 4.5: Implement `GET /auth/me` (returns current authenticated user profile).
  - [x] Task 4.6: Implement `POST /auth/logout` (clears session cookies).
  - [x] Task 4.7: Register the auth router in [`app/main.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/main.py).

- [x] **Phase 5: Standalone JavaScript Frontend Client SDK**
  - [x] Task 5.1: Create standalone zero-dependency ES module [`app/static/Script/auth-client.js`](file:///Users/charliemarciano/workspace/projects/aistreamradio/app/static/Script/auth-client.js).
  - [x] Task 5.2: Implement `AuthClient` class with methods `login(provider)`, `logout()`, and `getUser()`.
  - [x] Task 5.3: Implement event listener system `onAuthStateChanged(callback)`.
  - [x] Task 5.4: Prepare integration hook for frontend client.

- [x] **Phase 6: Automated Testing & Standalone Verification**
  - [x] Task 6.1: Write unit tests for `AuthService` & JWT utilities in [`tests/test_auth_service.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_auth_service.py).
  - [x] Task 6.2: Write integration tests for FastAPI `/auth/*` endpoints in [`tests/test_auth_router.py`](file:///Users/charliemarciano/workspace/projects/aistreamradio/tests/test_auth_router.py).
  - [x] Task 6.3: Verify modular extraction process by validating zero application-specific couplings.


---

## Detailed Task Breakdown

### Phase 1: Environment & Dependency Configuration
#### Task 1.1: Dependency Installation
- Add `Authlib >= 1.3.0`, `pyjwt >= 2.8.0`, `pydantic-settings >= 2.0.0` to `pyproject.toml`.
- Run dependency resolution to update lockfile.

#### Task 1.2: Configuration Setup
- Create `AuthSettings` class in `app/Configuration/auth_config.py` inheriting from `BaseSettings`.
- Declare environment variables:
  - `AUTH_SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `SESSION_COOKIE_NAME`, `COOKIE_SECURE`, `COOKIE_SAMESITE`.
  - Provider keys: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`.

---

### Phase 2: Database Schema & ORM Repositories
#### Task 2.1: Declarative ORM Models
- Define `User` table with `id`, `email`, `full_name`, `avatar_url`, `is_active`, `is_superuser`, `created_at`, `updated_at`.
- Define `OAuthAccount` table with `id`, `user_id` (FK), `provider`, `provider_user_id`, `email_at_provider`, `created_at`.

#### Task 2.2: Schemas & DTOs
- Create `UserRead`, `TokenPayload`, `OAuthProviderInfo`, and `SessionResponse` schemas.

#### Task 2.3: Repository Layer
- Create `UserRepository` in `app/repositories/users.py`:
  - `get_by_email(email: str)`
  - `get_by_oauth(provider: str, provider_user_id: str)`
  - `create_user_with_oauth(profile_data: dict)`

---

### Phase 3: Security Core & Auth Service
#### Task 3.1: Token Utilities
- Functions: `create_access_token()`, `decode_access_token()`.
- Error handling for expired or tampered signatures using standard JWT exceptions.

#### Task 3.2: AuthService Implementation
- Initialize Authlib `OAuth` registry with Google and Microsoft configs.
- Implement `get_login_redirect(request, provider, redirect_uri)`.
- Implement `handle_callback(request, provider)` returning normalized identity object (`provider`, `provider_user_id`, `email`, `full_name`, `avatar_url`).

#### Task 3.3: Protected Route Dependency
- Implement `get_current_user(request, db)` dependency that parses either the `app_session` cookie or `Authorization: Bearer <token>` header.

---

### Phase 4: Backend REST API Router & Endpoints
#### Task 4.1 - 4.6: Auth API Routes
- Build router `/auth` with all specified endpoints.
- Ensure cookie setup on `/auth/callback/{provider}`: `HttpOnly`, `SameSite=Lax`, `Secure`, `Max-Age`.
- Ensure cookie deletion on `/auth/logout`.

---

### Phase 5: Standalone JavaScript Frontend Client SDK
#### Task 5.1 - 5.3: `AuthClient` Class (`auth-client.js`)
- Construct zero-dependency ES module class.
- Methods:
  - `login(provider)` -> redirects window to `/auth/login/{provider}`.
  - `getUser()` -> performs `fetch('/auth/me', { credentials: 'include' })`.
  - `logout()` -> performs `POST /auth/logout`.
  - `onAuthStateChanged(callback)` -> pub/sub listener registration.

#### Task 5.4: UI Wire-up (`main.js`)
- Instantiate `AuthClient` and connect user profile state to top navigation HUD.

---

### Phase 6: Automated Testing & Verification
#### Task 6.1 - 6.2: Automated Test Suite
- Use `pytest` and `TestClient` to verify router endpoints.
- Mock external OAuth code exchanges to test database user creation and session cookie setting without live API calls.
