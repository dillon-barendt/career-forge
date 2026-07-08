import json
import os
from pathlib import Path

from pydantic import BaseModel, Field

from career_ops.config import Settings


class SetupCheck(BaseModel):
    name: str
    ready: bool
    detail: str


class ExternalSetupReport(BaseModel):
    items: list[SetupCheck] = Field(default_factory=list)

    @property
    def overall_ready(self) -> bool:
        return bool(self.items) and all(item.ready for item in self.items)


def check_external_setup(settings: Settings) -> ExternalSetupReport:
    items = [
        _gmail_credentials_check(settings),
        _openai_check(settings),
        _logfire_check(settings),
        _notion_check(settings),
    ]
    return ExternalSetupReport(items=items)


def _gmail_credentials_check(settings: Settings) -> SetupCheck:
    path = settings.gmail_credentials_path
    if not path.exists():
        return SetupCheck(
            name="Gmail OAuth credentials",
            ready=False,
            detail=f"Missing file: {path}",
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return SetupCheck(name="Gmail OAuth credentials", ready=False, detail="Invalid JSON.")

    client = data.get("installed") or data.get("web")
    if not isinstance(client, dict):
        return SetupCheck(
            name="Gmail OAuth credentials",
            ready=False,
            detail="Expected an 'installed' or 'web' OAuth client object.",
        )

    has_client_id = bool(client.get("client_id"))
    has_client_secret = bool(client.get("client_secret"))
    if has_client_id and has_client_secret:
        return SetupCheck(
            name="Gmail OAuth credentials",
            ready=True,
            detail="Credential file is present and structurally valid.",
        )
    return SetupCheck(
        name="Gmail OAuth credentials",
        ready=False,
        detail="Credential file is missing client_id or client_secret.",
    )


def _openai_check(settings: Settings) -> SetupCheck:
    has_key = bool(os.getenv("OPENAI_API_KEY") or settings.openai_api_key)
    return SetupCheck(
        name="OpenAI API key",
        ready=has_key,
        detail="Configured." if has_key else "Set OPENAI_API_KEY or CAREER_FORGE_OPENAI_API_KEY.",
    )


def _logfire_check(settings: Settings) -> SetupCheck:
    local_auth_project = _local_logfire_project()
    has_token = bool(os.getenv("LOGFIRE_TOKEN") or settings.logfire_token)
    ready = has_token or local_auth_project is not None or bool(
        settings.logfire_project and settings.logfire_base_url
    )
    target = local_auth_project or f"{settings.logfire_project} at {settings.logfire_base_url}"
    return SetupCheck(
        name="Logfire",
        ready=ready,
        detail=(
            f"Target {target}."
            if ready
            else "Run logfire auth/projects use or set LOGFIRE_TOKEN."
        ),
    )


def _local_logfire_project() -> str | None:
    credentials_path = Path(".logfire/logfire_credentials.json")
    if not credentials_path.exists():
        return None
    try:
        payload = json.loads(credentials_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    project_url = payload.get("project_url")
    if isinstance(project_url, str) and project_url:
        return project_url
    project_name = payload.get("project_name")
    if isinstance(project_name, str) and project_name:
        return project_name
    return None


def _notion_check(settings: Settings) -> SetupCheck:
    required_database_ids = [
        settings.opportunities_database_id,
        settings.companies_database_id,
        settings.contacts_database_id,
        settings.applications_database_id,
    ]
    ready = settings.notion_token is not None and all(required_database_ids)
    return SetupCheck(
        name="Notion API",
        ready=ready,
        detail=(
            "Token and core database IDs are configured."
            if ready
            else "Set CAREER_FORGE_NOTION_TOKEN and core database IDs."
        ),
    )
