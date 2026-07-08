from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    notion_token: SecretStr | None = Field(default=None)
    notion_version: str = "2022-06-28"
    opportunities_database_id: str | None = None
    companies_database_id: str | None = None
    contacts_database_id: str | None = None
    applications_database_id: str | None = None
    materials_database_id: str | None = None
    interviews_database_id: str | None = None
    followups_database_id: str | None = None
    outreach_templates_database_id: str | None = None
    research_notes_database_id: str | None = None
    tasks_database_id: str | None = None
    weekly_reviews_database_id: str | None = None
    sqlite_path: Path = Path(".career_ops/cache.sqlite3")
    gmail_account: str = "dillon.barendt.jobs@gmail.com"
    gmail_credentials_path: Path = Path(".career_ops/gmail_credentials.json")
    gmail_token_path: Path = Path(".career_ops/gmail_token.json")
    gmail_processed_label: str = "Career Ops/Processed"
    ai_provider: str = "deterministic"
    pydantic_ai_model: str = "openai:gpt-5.2"
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("CAREER_OPS_OPENAI_API_KEY", "OPENAI_API_KEY"),
    )
    job_fetch_timeout_seconds: float = 20.0
    state_path: Path = Path(".career_ops/state.json")
    event_log_path: Path = Path(".career_ops/events.jsonl")
    logfire_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("CAREER_OPS_LOGFIRE_TOKEN", "LOGFIRE_TOKEN"),
    )
    logfire_environment: str = "local"
    logfire_base_url: str = "https://logfire-us.pydantic.dev"
    logfire_project: str = "dillon-barendt/career-ops"
    logfire_service_name: str = "career-ops"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CAREER_OPS_",
        extra="ignore",
    )

    @property
    def has_notion_credentials(self) -> bool:
        return self.notion_token is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
