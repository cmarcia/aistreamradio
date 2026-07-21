from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite lives in ./data so it can be mounted as a Docker volume and
    # survive container rebuilds.
    database_url: str = "sqlite:///./data/radiostation.db"
    app_name: str = "AI Stream Radio API"
    disliked_songs_page_size: int = 5


settings = Settings()
