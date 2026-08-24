import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from career_ops.ai.factory import AIConfigurationError, resolve_real_provider_configuration
from career_ops.compat import StrEnum
from career_ops.config import RuntimeMode, Settings


class SetupStatus(StrEnum):
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"


class SetupValidationItem(BaseModel):
    name: str
    status: SetupStatus
    detail: str
    suggested_fix: str = ""
    env_var: str | None = None


class SetupValidationReport(BaseModel):
    items: list[SetupValidationItem] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(item.status == SetupStatus.ERROR for item in self.items)


def validate_setup(settings: Settings) -> SetupValidationReport:
    return SetupValidationReport(
        items=[
            *_runtime_path_checks(settings),
            _gmail_credentials_check(settings),
            _gmail_token_check(settings),
            _notion_check(settings),
            _ai_provider_check(settings),
            _logfire_check(settings),
            _event_log_check(settings),
            _dry_run_safety_check(),
        ]
    )


def _runtime_path_checks(settings: Settings) -> list[SetupValidationItem]:
    return [
        _path_parent_check(
            name="Runtime state directory",
            path=settings.state_path,
            env_var="CAREER_FORGE_STATE_PATH",
        ),
        _path_parent_check(
            name="SQLite cache directory",
            path=settings.sqlite_path,
            env_var="CAREER_FORGE_SQLITE_PATH",
        ),
    ]


def _path_parent_check(*, name: str, path: Path, env_var: str) -> SetupValidationItem:
    parent = path.parent
    if parent.exists() and parent.is_dir():
        return SetupValidationItem(
            name=name,
            status=SetupStatus.OK,
            detail=f"Path parent exists: {parent}",
            env_var=env_var,
        )
    return SetupValidationItem(
        name=name,
        status=SetupStatus.WARNING,
        detail=f"Path parent will be created on first write: {parent}",
        suggested_fix=f"Create {parent} or choose a writable path.",
        env_var=env_var,
    )


def _gmail_credentials_check(settings: Settings) -> SetupValidationItem:
    path = settings.gmail_credentials_path
    if not path.exists():
        return SetupValidationItem(
            name="Gmail OAuth credentials",
            status=SetupStatus.ERROR,
            detail="Missing credential file.",
            suggested_fix="Create a Google OAuth client JSON file for the career inbox.",
            env_var="CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return SetupValidationItem(
            name="Gmail OAuth credentials",
            status=SetupStatus.ERROR,
            detail="Credential file is malformed JSON.",
            suggested_fix="Replace the file with a valid OAuth client JSON export.",
            env_var="CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        )
    client = data.get("installed") or data.get("web")
    if not isinstance(client, dict):
        return SetupValidationItem(
            name="Gmail OAuth credentials",
            status=SetupStatus.ERROR,
            detail="Credential file is missing an installed/web OAuth client object.",
            suggested_fix="Download the OAuth client JSON from Google Cloud Console.",
            env_var="CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        )
    if client.get("client_id") and client.get("client_secret"):
        return SetupValidationItem(
            name="Gmail OAuth credentials",
            status=SetupStatus.OK,
            detail="Credential file is present and structurally valid.",
            env_var="CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        )
    return SetupValidationItem(
        name="Gmail OAuth credentials",
        status=SetupStatus.ERROR,
        detail="Credential file is missing client_id or client_secret.",
        suggested_fix="Download a complete OAuth client JSON file.",
        env_var="CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
    )


def _gmail_token_check(settings: Settings) -> SetupValidationItem:
    if settings.gmail_token_path.exists():
        return SetupValidationItem(
            name="Gmail OAuth token",
            status=SetupStatus.OK,
            detail="Token cache is present.",
            env_var="CAREER_FORGE_GMAIL_TOKEN_PATH",
        )
    return SetupValidationItem(
        name="Gmail OAuth token",
        status=SetupStatus.WARNING,
        detail="Token cache is missing; first OAuth run will create it.",
        suggested_fix="Run a Gmail command after configuring OAuth credentials.",
        env_var="CAREER_FORGE_GMAIL_TOKEN_PATH",
    )


def _notion_check(settings: Settings) -> SetupValidationItem:
    missing = [
        env_var
        for value, env_var in (
            (settings.notion_token, "CAREER_FORGE_NOTION_TOKEN"),
            (settings.opportunities_database_id, "CAREER_FORGE_OPPORTUNITIES_DATABASE_ID"),
            (settings.companies_database_id, "CAREER_FORGE_COMPANIES_DATABASE_ID"),
            (settings.contacts_database_id, "CAREER_FORGE_CONTACTS_DATABASE_ID"),
            (settings.applications_database_id, "CAREER_FORGE_APPLICATIONS_DATABASE_ID"),
        )
        if not value
    ]
    if not missing:
        return SetupValidationItem(
            name="Notion API",
            status=SetupStatus.OK,
            detail="Token and core database IDs are configured.",
            env_var="CAREER_FORGE_NOTION_TOKEN",
        )
    return SetupValidationItem(
        name="Notion API",
        status=SetupStatus.ERROR,
        detail=f"Missing {len(missing)} required setting(s).",
        suggested_fix="Set the Notion token and core database IDs before live apply.",
        env_var=", ".join(missing),
    )


def _ai_provider_check(settings: Settings) -> SetupValidationItem:
    if settings.mode is RuntimeMode.MOCK:
        return SetupValidationItem(
            name="AI provider credentials",
            status=SetupStatus.OK,
            detail="Mock mode is deterministic and requires no AI credentials.",
            env_var="CAREER_FORGE_MODE",
        )
    try:
        resolve_real_provider_configuration(settings)
    except AIConfigurationError as exc:
        return SetupValidationItem(
            name="AI provider credentials",
            status=SetupStatus.ERROR,
            detail=str(exc),
            suggested_fix=f"Set {exc.env_var} before using real mode.",
            env_var=exc.env_var,
        )
    return SetupValidationItem(
        name="AI provider credentials",
        status=SetupStatus.OK,
        detail="Real-mode provider credentials are configured.",
        env_var=(
            "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY"
            if settings.pydantic_ai_gateway_enabled
            else "CAREER_FORGE_OPENAI_API_KEY"
        ),
    )


def _logfire_check(settings: Settings) -> SetupValidationItem:
    if settings.logfire_token is not None or os.getenv("LOGFIRE_TOKEN"):
        return SetupValidationItem(
            name="Logfire",
            status=SetupStatus.OK,
            detail="Write token is configured.",
            env_var="CAREER_FORGE_LOGFIRE_TOKEN",
        )
    if settings.logfire_project and settings.logfire_base_url:
        return SetupValidationItem(
            name="Logfire",
            status=SetupStatus.WARNING,
            detail="Project target is configured but no write token is present.",
            suggested_fix="Set CAREER_FORGE_LOGFIRE_TOKEN to emit traces.",
            env_var="CAREER_FORGE_LOGFIRE_TOKEN",
        )
    return SetupValidationItem(
        name="Logfire",
        status=SetupStatus.WARNING,
        detail="Logfire is not configured; local no-op tracing will be used.",
        suggested_fix="Run logfire auth or set CAREER_FORGE_LOGFIRE_TOKEN.",
        env_var="CAREER_FORGE_LOGFIRE_TOKEN",
    )


def _event_log_check(settings: Settings) -> SetupValidationItem:
    parent = settings.event_log_path.parent
    if parent.exists() and parent.is_dir():
        return SetupValidationItem(
            name="Event log storage",
            status=SetupStatus.OK,
            detail=f"Event log parent exists: {parent}",
            env_var="CAREER_FORGE_EVENT_LOG_PATH",
        )
    return SetupValidationItem(
        name="Event log storage",
        status=SetupStatus.WARNING,
        detail=f"Event log parent will be created on first write: {parent}",
        suggested_fix=f"Create {parent} or choose a writable event-log path.",
        env_var="CAREER_FORGE_EVENT_LOG_PATH",
    )


def _dry_run_safety_check() -> SetupValidationItem:
    return SetupValidationItem(
        name="Dry-run safety defaults",
        status=SetupStatus.OK,
        detail="Gmail ingestion and Notion apply commands default to dry-run.",
        suggested_fix="Use explicit --confirm for live mutation apply.",
    )
