from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.Configuration.auth_config import auth_settings
from app import models
from app.repositories.deps import get_user_repository
from app.repositories.users import UserRepository
from app.schemas.auth import UserRead, UserRegister, UserLogin

from app.services.auth_service import AuthService
from app.utilities.auth import create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/providers")
def list_providers():
    """Lists enabled OAuth identity providers."""
    providers = AuthService.list_enabled_providers()
    return {"providers": providers}


@router.get("/login/{provider}")
async def login_provider(
    provider: str,
    request: Request,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Initiates OAuth authorization code flow for the specified provider."""
    if provider == "demo":
        # Handle demo quick sign-in
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




@router.post("/dev-login")
def dev_login(
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Programmatic login for development and testing."""
    from app.Configuration.config import settings
    if settings.environment.lower() != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Development login endpoint is disabled in non-development environments.",
        )
    user = user_repo.upsert_from_oauth({

        "provider": "demo",
        "provider_user_id": "demo-user-123",
        "email": "listener@aistreamradio.com",
        "full_name": "AI Radio Listener",
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=RadioListener",
    })
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
    return {"message": "Successfully logged in as Demo Listener", "user": UserRead.model_validate(user)}



@router.get("/callback/{provider}", name="auth_callback")
async def auth_callback(
    provider: str,
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Handles OAuth callback redirect from provider."""
    auth_service = AuthService(user_repo)
    try:
        result = await auth_service.handle_callback(request, provider)
        user: models.User = result["user"]

        # Create session JWT
        token_data = {"sub": user.id, "email": user.email}
        access_token = create_access_token(token_data)

        # Set HttpOnly session cookie & redirect to main app
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key=auth_settings.session_cookie_name,
            value=access_token,
            httponly=True,
            secure=auth_settings.cookie_secure,
            samesite=auth_settings.cookie_samesite,
            max_age=auth_settings.access_token_expire_minutes * 60,
        )
        return response
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication callback failed: {str(exc)}",
        )


from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=UserRead)
@limiter.limit("10/minute")
def register_user(
    request: Request,
    data: UserRegister,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Registers a new user with email and password."""
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


@router.post("/login", response_model=UserRead)
@limiter.limit("15/minute")
def login_with_password(
    request: Request,
    data: UserLogin,
    response: Response,
    user_repo: UserRepository = Depends(get_user_repository),
):

    """Authenticates an existing user with email and password."""
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


@router.get("/me", response_model=UserRead)
def get_me(current_user: models.User = Depends(get_current_user)):
    """Returns current authenticated user profile."""
    return current_user



@router.post("/logout")
def logout(response: Response):
    """Clears the session cookie."""
    response.delete_cookie(key=auth_settings.session_cookie_name)
    return {"message": "Successfully logged out"}
