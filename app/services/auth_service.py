from typing import Any
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from app.Configuration.auth_config import auth_settings
from app.repositories.users import UserRepository

oauth = OAuth()

# Dynamically Register Google Provider if credentials present
if auth_settings.google_client_id and auth_settings.google_client_secret:
    oauth.register(
        name="google",
        client_id=auth_settings.google_client_id,
        client_secret=auth_settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )

# Dynamically Register Microsoft Provider if credentials present
if auth_settings.microsoft_client_id and auth_settings.microsoft_client_secret:
    tenant_id = auth_settings.microsoft_tenant_id or "common"
    oauth.register(
        name="microsoft",
        client_id=auth_settings.microsoft_client_id,
        client_secret=auth_settings.microsoft_client_secret,
        server_metadata_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )



class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    def list_enabled_providers() -> list[dict[str, str]]:
        enabled = []
        # Return list of registered providers in oauth registry
        for name in ["google", "microsoft"]:
            client = getattr(oauth, name, None)
            if client is not None:
                enabled.append({
                    "id": name,
                    "name": name.capitalize(),
                    "icon_url": f"/static/Images/{name}-icon.svg",
                })
        # Always provide a demo provider for quick testing/development
        if not enabled:
            enabled.append({
                "id": "demo",
                "name": "Demo Quick Login",
                "icon_url": None,
            })
        return enabled


    async def get_login_redirect(
        self, request: Request, provider: str, redirect_uri: str
    ):
        client = getattr(oauth, provider, None)
        if client is None:
            raise ValueError(f"OAuth provider '{provider}' is not configured.")
        return await client.authorize_redirect(request, redirect_uri)

    async def handle_callback(
        self, request: Request, provider: str
    ) -> dict[str, Any]:
        client = getattr(oauth, provider, None)
        if client is None:
            raise ValueError(f"OAuth provider '{provider}' is not configured.")

        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo")
        if not user_info:
            user_info = await client.userinfo(request, token=token)

        email = user_info.get("email")
        if not email:
            raise ValueError(f"Provider '{provider}' did not return a valid email address.")

        provider_user_id = str(user_info.get("sub") or user_info.get("id"))
        full_name = user_info.get("name") or user_info.get("full_name")
        avatar_url = user_info.get("picture") or user_info.get("avatar_url")

        normalized_profile = {
            "provider": provider,
            "provider_user_id": provider_user_id,
            "email": email,
            "full_name": full_name,
            "avatar_url": avatar_url,
        }

        # Upsert user record and link OAuth account
        user = self.user_repo.upsert_from_oauth(normalized_profile)
        return {
            "user": user,
            "profile": normalized_profile,
        }
