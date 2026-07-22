from typing import Any
from fastapi import Request
from starlette.responses import RedirectResponse

from app.config import auth_settings
from app.repositories.users import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    @staticmethod
    def list_enabled_providers() -> list[str]:
        providers = []
        if auth_settings.google_client_id and auth_settings.google_client_secret:
            providers.append("google")
        if auth_settings.microsoft_client_id and auth_settings.microsoft_client_secret:
            providers.append("microsoft")
        return providers

    async def get_login_redirect(self, request: Request, provider: str, redirect_uri: str) -> RedirectResponse:
        raise ValueError(f"OAuth provider '{provider}' is not configured.")

    async def handle_callback(self, request: Request, provider: str) -> dict[str, Any]:
        raise ValueError(f"OAuth provider '{provider}' callback is not configured.")
