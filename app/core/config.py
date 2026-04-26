from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UNS API"
    app_env: str = "local"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_database_url: str | None = "postgresql://postgres:postgres@localhost:55432/uns"
    app_database_path: str | None = None
    app_secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60

    @property
    def database_url(self) -> str:
        database_url = self.app_database_url
        if database_url:
            if database_url.startswith("postgres://"):
                return database_url.replace(
                    "postgres://",
                    "postgresql+psycopg://",
                    1,
                )
            if database_url.startswith("postgresql://"):
                return database_url.replace(
                    "postgresql://",
                    "postgresql+psycopg://",
                    1,
                )
            return database_url

        database_path = self.app_database_path or "uns.db"
        return f"sqlite:///{database_path}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
