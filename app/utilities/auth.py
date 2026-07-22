from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.Configuration.auth_config import auth_settings
from app import models
from app.repositories.users import UserRepository
from app.schemas.auth import TokenPayload
from app.utilities.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}${key.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, key_hex = hashed_password.split("$", 1)
        expected_key = bytes.fromhex(key_hex)
        key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(key, expected_key)
    except Exception:
        return False



def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=auth_settings.access_token_expire_minutes)
    )
    to_encode.update(
        {
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "iss": "aistreamradio-auth",
        }
    )
    return jwt.encode(
        to_encode,
        auth_settings.auth_secret_key,
        algorithm=auth_settings.auth_algorithm,
    )


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(
            token,
            auth_settings.auth_secret_key,
            algorithms=[auth_settings.auth_algorithm],
        )
        return TokenPayload(**payload)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_token_from_request(request: Request) -> str | None:
    # 1. Check Cookie first
    cookie_token = request.cookies.get(auth_settings.session_cookie_name)
    if cookie_token:
        return cookie_token

    # 2. Check Authorization Bearer header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()

    return None


def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User | None:
    token = _extract_token_from_request(request)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_repo = UserRepository(db)
        user = user_repo.get_by_id(payload.sub)
        if user and user.is_active:
            return user
    except HTTPException:
        pass

    return None


def get_current_user(
    request: Request, db: Session = Depends(get_db)
) -> models.User:
    user = get_optional_user(request, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were missing or invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
