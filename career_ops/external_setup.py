import json
import os

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
    has_token_or_local_auth = bool(os.getenv("LOGFIRE_TOKEN") or settings.logfire_token)
    local_auth_exists = bool(settings.logfire_project and settings.logfire_base_url)
    ready = has_token_or_local_auth or local_auth_exists
    return SetupCheck(
        name="Logfire",
        ready=ready,
        detail=(
            f"Target {settings.logfire_project} at {settings.logfire_base_url}."
            if ready
            else "Run logfire auth/projects use or set LOGFIRE_TOKEN."
        ),
    )


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
