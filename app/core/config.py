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
    jira_base_url: str | None = None
    jira_email: str | None = None
    jira_api_token: str | None = None
    jira_default_board_ids: str = ""
    jira_story_points_field: str | None = None
    jira_timeout_seconds: float = 20.0
    linear_api_url: str = "https://api.linear.app/graphql"
    linear_api_key: str | None = None
    linear_default_team_ids: str = ""
    linear_timeout_seconds: float = 20.0

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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
