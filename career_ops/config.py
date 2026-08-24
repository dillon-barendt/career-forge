from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from career_ops.compat import StrEnum


class RuntimeMode(StrEnum):
    """Selects deterministic mock execution or configured real-provider execution."""

    MOCK = "mock"
    REAL = "real"


def env_alias(name: str) -> AliasChoices:
    return AliasChoices(f"CAREER_FORGE_{name}", f"CAREER_OPS_{name}")


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env."""

    mode: RuntimeMode = Field(default=RuntimeMode.MOCK, validation_alias=env_alias("MODE"))
    notion_token: SecretStr | None = Field(default=None, validation_alias=env_alias("NOTION_TOKEN"))
    notion_version: str = Field(default="2022-06-28", validation_alias=env_alias("NOTION_VERSION"))
    opportunities_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("OPPORTUNITIES_DATABASE_ID"),
    )
    companies_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("COMPANIES_DATABASE_ID"),
    )
    contacts_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("CONTACTS_DATABASE_ID"),
    )
    applications_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("APPLICATIONS_DATABASE_ID"),
    )
    materials_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("MATERIALS_DATABASE_ID"),
    )
    interviews_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("INTERVIEWS_DATABASE_ID"),
    )
    followups_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("FOLLOWUPS_DATABASE_ID"),
    )
    outreach_templates_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("OUTREACH_TEMPLATES_DATABASE_ID"),
    )
    research_notes_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("RESEARCH_NOTES_DATABASE_ID"),
    )
    tasks_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("TASKS_DATABASE_ID"),
    )
    weekly_reviews_database_id: str | None = Field(
        default=None,
        validation_alias=env_alias("WEEKLY_REVIEWS_DATABASE_ID"),
    )
    sqlite_path: Path = Field(
        default=Path(".career_forge/cache.sqlite3"),
        validation_alias=env_alias("SQLITE_PATH"),
    )
    gmail_account: str = Field(
        default="dillon.barendt.jobs@gmail.com",
        validation_alias=env_alias("GMAIL_ACCOUNT"),
    )
    gmail_credentials_path: Path = Field(
        default=Path(".career_forge/gmail_credentials.json"),
        validation_alias=env_alias("GMAIL_CREDENTIALS_PATH"),
    )
    gmail_token_path: Path = Field(
        default=Path(".career_forge/gmail_token.json"),
        validation_alias=env_alias("GMAIL_TOKEN_PATH"),
    )
    gmail_processed_label: str = Field(
        default="Career Forge/Processed",
        validation_alias=env_alias("GMAIL_PROCESSED_LABEL"),
    )
    ai_provider: str = Field(default="deterministic", validation_alias=env_alias("AI_PROVIDER"))
    pydantic_ai_model: str = Field(
        default="openai:gpt-5.2",
        validation_alias=env_alias("PYDANTIC_AI_MODEL"),
    )
    pydantic_ai_gateway_enabled: bool = Field(
        default=False,
        validation_alias=env_alias("PYDANTIC_AI_GATEWAY_ENABLED"),
    )
    pydantic_ai_gateway_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
            "PYDANTIC_AI_GATEWAY_API_KEY",
        ),
    )
    pydantic_ai_gateway_provider: str = Field(
        default="openai",
        validation_alias=env_alias("PYDANTIC_AI_GATEWAY_PROVIDER"),
    )
    pydantic_ai_gateway_route: str | None = Field(
        default=None,
        validation_alias=env_alias("PYDANTIC_AI_GATEWAY_ROUTE"),
    )
    openai_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CAREER_FORGE_OPENAI_API_KEY",
            "CAREER_OPS_OPENAI_API_KEY",
            "OPENAI_API_KEY",
        ),
    )
    job_fetch_timeout_seconds: float = Field(
        default=20.0,
        validation_alias=env_alias("JOB_FETCH_TIMEOUT_SECONDS"),
    )
    state_path: Path = Field(
        default=Path(".career_forge/state.json"),
        validation_alias=env_alias("STATE_PATH"),
    )
    event_log_path: Path = Field(
        default=Path(".career_forge/events.jsonl"),
        validation_alias=env_alias("EVENT_LOG_PATH"),
    )
    logfire_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "CAREER_FORGE_LOGFIRE_TOKEN",
            "CAREER_OPS_LOGFIRE_TOKEN",
            "LOGFIRE_TOKEN",
        ),
    )
    logfire_environment: str = Field(
        default="local",
        validation_alias=env_alias("LOGFIRE_ENVIRONMENT"),
    )
    logfire_base_url: str = Field(
        default="https://logfire-us.pydantic.dev",
        validation_alias=env_alias("LOGFIRE_BASE_URL"),
    )
    logfire_project: str = Field(
        default="dillon-barendt/career-forge",
        validation_alias=env_alias("LOGFIRE_PROJECT"),
    )
    logfire_service_name: str = Field(
        default="career-forge",
        validation_alias=env_alias("LOGFIRE_SERVICE_NAME"),
    )
    logfire_metrics_enabled: bool = Field(
        default=True,
        validation_alias=env_alias("LOGFIRE_METRICS_ENABLED"),
    )
    logfire_variables_enabled: bool = Field(
        default=True,
        validation_alias=env_alias("LOGFIRE_VARIABLES_ENABLED"),
    )
    logfire_instrument_httpx: bool = Field(
        default=True,
        validation_alias=env_alias("LOGFIRE_INSTRUMENT_HTTPX"),
    )
    logfire_instrument_openai: bool = Field(
        default=True,
        validation_alias=env_alias("LOGFIRE_INSTRUMENT_OPENAI"),
    )
    logfire_instrument_system_metrics: bool = Field(
        default=False,
        validation_alias=env_alias("LOGFIRE_INSTRUMENT_SYSTEM_METRICS"),
    )
    webhooks_enabled: bool = Field(default=True, validation_alias=env_alias("WEBHOOKS_ENABLED"))
    webhooks_public_base_url: str = Field(
        default="https://hooks.concordmanage.com",
        validation_alias=env_alias("WEBHOOKS_PUBLIC_BASE_URL"),
    )
    webhooks_default_project: str = Field(
        default="career-forge",
        validation_alias=env_alias("WEBHOOKS_DEFAULT_PROJECT"),
    )
    webhooks_notion_enabled: bool = Field(
        default=True,
        validation_alias=env_alias("WEBHOOKS_NOTION_ENABLED"),
    )
    webhooks_notion_secret: SecretStr | None = Field(
        default=None,
        validation_alias=env_alias("WEBHOOKS_NOTION_SECRET"),
    )
    webhooks_github_enabled: bool = Field(
        default=True,
        validation_alias=env_alias("WEBHOOKS_GITHUB_ENABLED"),
    )
    webhooks_github_secret: SecretStr | None = Field(
        default=None,
        validation_alias=env_alias("WEBHOOKS_GITHUB_SECRET"),
    )
    webhooks_max_body_bytes: int = Field(
        default=1_048_576,
        validation_alias=env_alias("WEBHOOKS_MAX_BODY_BYTES"),
    )
    webhooks_log_payloads: bool = Field(
        default=False,
        validation_alias=env_alias("WEBHOOKS_LOG_PAYLOADS"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def has_notion_credentials(self) -> bool:
        return self.notion_token is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()
