from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_secret_key: str = "CHANGE_THIS_IN_PRODUCTION_SECRET_KEY_MIN_32_BYTES"
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 Hours
    session_cookie_name: str = "app_session"
    cookie_secure: bool = False  # Set True in production (HTTPS)
    cookie_samesite: str = "lax"

    # OAuth Provider Keys
    google_client_id: str | None = None
    google_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None


auth_settings = AuthSettings()
