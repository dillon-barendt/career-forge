import json

from career_ops.cli import app
from career_ops.config import Settings
from career_ops.external_setup import check_external_setup
from typer.testing import CliRunner


def test_external_setup_detects_safe_local_credentials(tmp_path, monkeypatch) -> None:
    credentials_path = tmp_path / "gmail_credentials.json"
    credentials_path.write_text(
        json.dumps(
            {
                "installed": {
                    "client_id": "example.apps.googleusercontent.com",
                    "client_secret": "example-secret",
                    "redirect_uris": ["http://localhost"],
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LOGFIRE_TOKEN", "lf-test")

    report = check_external_setup(
        Settings(
            notion_token="secret_test",
            opportunities_database_id="opportunities",
            companies_database_id="companies",
            contacts_database_id="contacts",
            applications_database_id="applications",
            gmail_credentials_path=credentials_path,
        )
    )

    assert report.overall_ready is True
    assert all(item.ready for item in report.items)


def test_check_setup_cli_does_not_print_secret_values(tmp_path, monkeypatch) -> None:
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
    monkeypatch.setenv("CAREER_FORGE_GMAIL_CREDENTIALS_PATH", str(credentials_path))
    monkeypatch.setenv("CAREER_FORGE_NOTION_TOKEN", "secret_do_not_print")
    monkeypatch.setenv("CAREER_FORGE_OPPORTUNITIES_DATABASE_ID", "opportunities")
    monkeypatch.setenv("CAREER_FORGE_COMPANIES_DATABASE_ID", "companies")
    monkeypatch.setenv("CAREER_FORGE_CONTACTS_DATABASE_ID", "contacts")
    monkeypatch.setenv("CAREER_FORGE_APPLICATIONS_DATABASE_ID", "applications")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-do-not-print")
    monkeypatch.setenv("LOGFIRE_TOKEN", "lf-do-not-print")

    result = CliRunner().invoke(app, ["check-setup"])

    assert result.exit_code == 0
    assert "External Setup" in result.stdout
    assert "do-not-print" not in result.stdout
    assert "secret_do_not_print" not in result.stdout
    assert "sk-do-not-print" not in result.stdout


def test_external_setup_logfire_check_accepts_project_config_without_token() -> None:
    report = check_external_setup(
        Settings(
            openai_api_key="sk-test",
            notion_token="secret_test",
            opportunities_database_id="opportunities",
            companies_database_id="companies",
            contacts_database_id="contacts",
            applications_database_id="applications",
        )
    )

    logfire = next(item for item in report.items if item.name == "Logfire")

    assert logfire.ready is True
