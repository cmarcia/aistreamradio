from datetime import timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.repositories.users import UserRepository
from app.services.auth_service import AuthService
from app.utilities.auth import create_access_token, decode_access_token
from app.utilities.database import Base


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_jwt_token_creation_and_decoding():
    data = {"sub": "user-uuid-123", "email": "test@example.com"}
    token = create_access_token(data, expires_delta=timedelta(minutes=30))
    assert isinstance(token, str)

    payload = decode_access_token(token)
    assert payload.sub == "user-uuid-123"
    assert payload.email == "test@example.com"
    assert payload.iss == "aistreamradio-auth"


def test_jwt_token_invalid_signature():
    invalid_token = "invalid.jwt.token"
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(invalid_token)
    assert exc_info.value.status_code == 401


def test_user_repository_upsert_new_user(db_session):
    repo = UserRepository(db_session)
    profile = {
        "provider": "google",
        "provider_user_id": "google-uid-100",
        "email": "alice@example.com",
        "full_name": "Alice Smith",
        "avatar_url": "https://example.com/avatar.jpg",
    }

    user = repo.upsert_from_oauth(profile)
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.full_name == "Alice Smith"
    assert user.avatar_url == "https://example.com/avatar.jpg"
    assert len(user.oauth_accounts) == 1
    assert user.oauth_accounts[0].provider == "google"
    assert user.oauth_accounts[0].provider_user_id == "google-uid-100"


def test_user_repository_account_linking(db_session):
    repo = UserRepository(db_session)

    # 1. First login with Google
    google_profile = {
        "provider": "google",
        "provider_user_id": "google-uid-100",
        "email": "bob@example.com",
        "full_name": "Bob Marley",
        "avatar_url": None,
    }
    user1 = repo.upsert_from_oauth(google_profile)

    # 2. Second login with Microsoft using same email
    ms_profile = {
        "provider": "microsoft",
        "provider_user_id": "ms-uid-200",
        "email": "bob@example.com",
        "full_name": "Bob Marley",
        "avatar_url": "https://example.com/bob.jpg",
    }
    user2 = repo.upsert_from_oauth(ms_profile)

    # Should link to same user record
    assert user1.id == user2.id
    assert len(user2.oauth_accounts) == 2
    providers = {acc.provider for acc in user2.oauth_accounts}
    assert providers == {"google", "microsoft"}


def test_auth_service_list_enabled_providers():
    providers = AuthService.list_enabled_providers()
    assert isinstance(providers, list)
