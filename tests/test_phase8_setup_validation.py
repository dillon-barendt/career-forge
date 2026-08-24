import json

from typer.testing import CliRunner

from career_ops.cli import app
from career_ops.config import Settings, get_settings
from career_ops.setup_validation import SetupStatus, validate_setup


def test_setup_validation_reports_valid_configuration(tmp_path) -> None:
    credentials_path = tmp_path / "gmail_credentials.json"
    credentials_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "example.apps.googleusercontent.com",
                    "client_secret": "do-not-print",
                }
            }
        ),
        encoding="utf-8",
    )
    settings = Settings(
        event_log_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
        gmail_credentials_path=credentials_path,
        gmail_token_path=tmp_path / "gmail_token.json",
        notion_token="secret_do_not_print",
        opportunities_database_id="opportunities",
        companies_database_id="companies",
        contacts_database_id="contacts",
        applications_database_id="applications",
        openai_api_key="sk-do-not-print",
        logfire_token="lf-do-not-print",
    )

    report = validate_setup(settings)

    assert report.has_errors is False
    assert all(item.status != SetupStatus.ERROR for item in report.items)


def test_setup_validation_mock_mode_does_not_require_ai_credentials(tmp_path, monkeypatch) -> None:
    for name in (
        "CAREER_FORGE_NOTION_TOKEN",
        "CAREER_FORGE_OPPORTUNITIES_DATABASE_ID",
        "CAREER_FORGE_COMPANIES_DATABASE_ID",
        "CAREER_FORGE_CONTACTS_DATABASE_ID",
        "CAREER_FORGE_APPLICATIONS_DATABASE_ID",
        "CAREER_FORGE_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
        "PYDANTIC_AI_GATEWAY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    report = validate_setup(
        Settings(
            event_log_path=tmp_path / "events.jsonl",
            state_path=tmp_path / "state.json",
            gmail_credentials_path=tmp_path / "missing_credentials.json",
            mode="mock",
            ai_provider="pydantic-ai",
            notion_token=None,
            opportunities_database_id=None,
            companies_database_id=None,
            contacts_database_id=None,
            applications_database_id=None,
            openai_api_key=None,
            pydantic_ai_gateway_api_key=None,
        )
    )

    by_name = {item.name: item for item in report.items}

    assert by_name["Gmail OAuth credentials"].status == SetupStatus.ERROR
    assert by_name["Notion API"].status == SetupStatus.ERROR
    assert by_name["AI provider credentials"].status == SetupStatus.OK
    assert by_name["Gmail OAuth credentials"].env_var == "CAREER_FORGE_GMAIL_CREDENTIALS_PATH"
    assert "Set" in by_name["Notion API"].suggested_fix


def test_setup_validation_real_mode_requires_ai_credentials(tmp_path, monkeypatch) -> None:
    for name in (
        "CAREER_FORGE_OPENAI_API_KEY",
        "CAREER_OPS_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
        "PYDANTIC_AI_GATEWAY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        mode="real",
        ai_provider="deterministic",
        pydantic_ai_model="openai:gpt-5.2",
        openai_api_key="   ",
        pydantic_ai_gateway_api_key=None,
        event_log_path=tmp_path / "events.jsonl",
        state_path=tmp_path / "state.json",
    )

    report = validate_setup(settings)
    item = next(item for item in report.items if item.name == "AI provider credentials")

    assert item.status == SetupStatus.ERROR
    assert item.env_var == "CAREER_FORGE_OPENAI_API_KEY"


def test_setup_validate_cli_redacts_secret_values(tmp_path, monkeypatch) -> None:
    credentials_path = tmp_path / "gmail_credentials.json"
    credentials_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "example.apps.googleusercontent.com",
                    "client_secret": "do-not-print",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv("CAREER_FORGE_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("CAREER_FORGE_GMAIL_CREDENTIALS_PATH", str(credentials_path))
    monkeypatch.setenv("CAREER_FORGE_NOTION_TOKEN", "secret_do_not_print")
    monkeypatch.setenv("CAREER_FORGE_OPPORTUNITIES_DATABASE_ID", "opportunities")
    monkeypatch.setenv("CAREER_FORGE_COMPANIES_DATABASE_ID", "companies")
    monkeypatch.setenv("CAREER_FORGE_CONTACTS_DATABASE_ID", "contacts")
    monkeypatch.setenv("CAREER_FORGE_APPLICATIONS_DATABASE_ID", "applications")
    monkeypatch.setenv("CAREER_FORGE_OPENAI_API_KEY", "sk-do-not-print")
    monkeypatch.setenv("CAREER_FORGE_LOGFIRE_TOKEN", "lf-do-not-print")
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(app, ["setup", "validate"])
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Setup Validation" in result.stdout
    assert "do-not-print" not in result.stdout
    assert "secret_do_not_print" not in result.stdout
    assert "sk-do-not-print" not in result.stdout
    assert "lf-do-not-print" not in result.stdout
