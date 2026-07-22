from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite lives in ./data so it can be mounted as a Docker volume and
    # survive container rebuilds.
    database_url: str = "sqlite:///./data/radiostation.db"
    app_name: str = "AI Stream Radio API"
    disliked_songs_page_size: int = 5
    default_primary_color: str = "#00f3ff"
    default_secondary_color: str = "#3b82f6"
    log_level: str = "INFO"
    environment: str = "development"


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    auth_secret_key: str = "super_secret_radio_jwt_key_change_me_in_prod"
    auth_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 Hours
    session_cookie_name: str = "app_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    google_client_id: str | None = None
    google_client_secret: str | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_tenant_id: str = "common"


settings = Settings()
auth_settings = AuthSettings()

