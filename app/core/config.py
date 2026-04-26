from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UNS API"
    app_env: str = "local"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_public_base_url: str = "http://localhost:8000"
    app_frontend_url: str = "http://localhost:5173"
    app_database_url: Optional[str] = "postgresql://postgres:postgres@localhost:55432/uns"
    app_database_path: Optional[str] = None
    app_cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    app_secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60
    jira_base_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None
    jira_default_board_ids: str = ""
    jira_story_points_field: Optional[str] = None
    jira_timeout_seconds: float = 20.0
    jira_oauth_client_id: Optional[str] = None
    jira_oauth_client_secret: Optional[str] = None
    jira_oauth_scopes: str = "read:jira-work offline_access"
    linear_api_url: str = "https://api.linear.app/graphql"
    linear_api_key: Optional[str] = None
    linear_default_team_ids: str = ""
    linear_timeout_seconds: float = 20.0
    linear_oauth_client_id: Optional[str] = None
    linear_oauth_client_secret: Optional[str] = None
    linear_oauth_scopes: str = "read,write"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    @property
    def jira_default_board_id_list(self) -> list[int]:
        values = []
        for raw_value in self.jira_default_board_ids.split(","):
            stripped = raw_value.strip()
            if not stripped:
                continue
            values.append(int(stripped))
        return values

    @property
    def linear_default_team_id_list(self) -> list[str]:
        return [
            raw_value.strip()
            for raw_value in self.linear_default_team_ids.split(",")
            if raw_value.strip()
        ]

    @property
    def normalized_public_base_url(self) -> str:
        return self.app_public_base_url.rstrip("/")

    @property
    def normalized_frontend_url(self) -> str:
        return self.app_frontend_url.rstrip("/")

    @property
    def jira_oauth_redirect_uri(self) -> str:
        return f"{self.normalized_public_base_url}/api/v1/integrations/oauth/jira/callback"

    @property
    def linear_oauth_redirect_uri(self) -> str:
        return f"{self.normalized_public_base_url}/api/v1/integrations/oauth/linear/callback"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
