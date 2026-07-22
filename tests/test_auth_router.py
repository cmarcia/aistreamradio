import pytest
from app.Configuration.auth_config import auth_settings
from app.utilities.auth import create_access_token


def test_list_auth_providers_endpoint(client):
    response = client.get("/auth/providers")
    assert response.status_code == 200
    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], list)


def test_login_unconfigured_provider(client):
    response = client.get("/auth/login/unconfigured_provider")
    assert response.status_code == 400
    assert "not configured" in response.json()["detail"]


def test_get_me_unauthenticated(client):
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication credentials were missing or invalid"


def test_get_me_with_valid_cookie(client):
    from app.repositories.deps import get_db
    from app.repositories.users import UserRepository

    with client:
        override_db = client.app.dependency_overrides[get_db]()
        db = next(override_db)
        repo = UserRepository(db)
        user = repo.upsert_from_oauth({
            "provider": "google",
            "provider_user_id": "google-user-999",
            "email": "user@example.com",
            "full_name": "Test User",
            "avatar_url": None,
        })

        # Create token using actual user.id
        token = create_access_token({"sub": user.id, "email": user.email})

        # Set cookie and call /auth/me
        client.cookies.set(auth_settings.session_cookie_name, token)
        response = client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["full_name"] == "Test User"



def test_logout_clears_cookie(client):
    client.cookies.set(auth_settings.session_cookie_name, "some-session-token")
    response = client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"


def test_register_and_login_with_email_password(client):
    # 1. Register new user
    reg_response = client.post("/auth/register", json={
        "email": "newlistener@cyber.io",
        "password": "securepassword123",
        "full_name": "New Listener"
    })
    assert reg_response.status_code == 200
    user_data = reg_response.json()
    assert user_data["email"] == "newlistener@cyber.io"
    assert user_data["full_name"] == "New Listener"

    # Verify session cookie was set
    assert auth_settings.session_cookie_name in client.cookies

    # 2. Check /auth/me
    me_response = client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "newlistener@cyber.io"

    # 3. Logout
    client.post("/auth/logout")

    # 4. Login with invalid password
    bad_login = client.post("/auth/login", json={
        "email": "newlistener@cyber.io",
        "password": "wrongpassword"
    })
    assert bad_login.status_code == 401

    # 5. Login with correct password
    good_login = client.post("/auth/login", json={
        "email": "newlistener@cyber.io",
        "password": "securepassword123"
    })
    assert good_login.status_code == 200
    assert good_login.json()["email"] == "newlistener@cyber.io"


def test_dev_login_disabled_in_production(client):
    from app.Configuration.config import settings
    original_env = settings.environment
    try:
        settings.environment = "production"
        res = client.post("/auth/dev-login")
        assert res.status_code == 403
        assert "disabled" in res.json()["detail"]
    finally:
        settings.environment = original_env


