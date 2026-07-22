from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from app import models, schemas
from app.config import auth_settings
from app.repositories.deps import get_user_repository
from app.repositories.users import UserRepository
from app.services.auth_service import AuthService
from app.utilities.auth import (
    create_access_token,
    get_current_user,
    get_optional_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/providers")
def list_providers():
    providers = AuthService.list_enabled_providers()
    return {"providers": providers}


@router.get("/login/{provider}")
async def login_provider(
    provider: str,
    request: Request,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    if provider == "demo":
        user = user_repo.upsert_from_oauth({
            "provider": "demo",
            "provider_user_id": "demo-user-123",
            "email": "listener@aistreamradio.com",
            "full_name": "AI Radio Listener",
            "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=RadioListener",
        })
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)

        redirect_response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key=auth_settings.session_cookie_name,
            value=access_token,
            httponly=True,
            secure=auth_settings.cookie_secure,
            samesite=auth_settings.cookie_samesite,
            max_age=auth_settings.access_token_expire_minutes * 60,
        )
        return redirect_response

    auth_service = AuthService(user_repo)
    redirect_uri = str(request.url_for("auth_callback", provider=provider))
    if request.headers.get("x-forwarded-proto") == "https" or request.headers.get("x-forwarded-ssl") == "on":
        redirect_uri = redirect_uri.replace("http://", "https://", 1)

    try:
        return await auth_service.get_login_redirect(request, provider, redirect_uri)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(
    provider: str,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
):
    auth_service = AuthService(user_repo)
    try:
        token = await auth_service.handle_callback(request, provider)
        user_info = token.get("userinfo") or {}
        email = user_info.get("email") or f"{provider}_user@aistreamradio.com"
        full_name = user_info.get("name") or user_info.get("preferred_username")

        user = user_repo.upsert_from_oauth({
            "provider": provider,
            "provider_user_id": user_info.get("sub") or "oauth-id",
            "email": email,
            "full_name": full_name,
            "avatar_url": user_info.get("picture"),
        })

        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)

        redirect_response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key=auth_settings.session_cookie_name,
            value=access_token,
            httponly=True,
            secure=auth_settings.cookie_secure,
            samesite=auth_settings.cookie_samesite,
            max_age=auth_settings.access_token_expire_minutes * 60,
        )
        return redirect_response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication callback failed: {str(exc)}",
        )


@router.post("/register", response_model=schemas.UserRead)
def register_user(
    data: schemas.UserRegister,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    try:
        user = user_repo.create_user_with_password(
            email=data.email,
            raw_password=data.password,
            full_name=data.full_name,
        )
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)

        response.set_cookie(
            key=auth_settings.session_cookie_name,
            value=access_token,
            httponly=True,
            secure=auth_settings.cookie_secure,
            samesite=auth_settings.cookie_samesite,
            max_age=auth_settings.access_token_expire_minutes * 60,
        )
        return user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )


@router.post("/login", response_model=schemas.UserRead)
def login_with_password(
    data: schemas.UserLogin,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    user = user_repo.authenticate_with_password(data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token_data = {"sub": user.id, "email": user.email}
    access_token = create_access_token(token_data)

    response.set_cookie(
        key=auth_settings.session_cookie_name,
        value=access_token,
        httponly=True,
        secure=auth_settings.cookie_secure,
        samesite=auth_settings.cookie_samesite,
        max_age=auth_settings.access_token_expire_minutes * 60,
    )
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(key=auth_settings.session_cookie_name)
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=schemas.UserRead)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user
