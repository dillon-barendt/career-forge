import pytest
from typer.testing import CliRunner

from career_ops.ai.factory import AIConfigurationError
from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.cli import app
from career_ops.config import get_settings
from career_ops.evals.runner import LogfireEvalRunner
from career_ops.ingestion.job_ingestion import JobIngestionPipeline

PUBLIC_AI_COMMANDS = [
    ["evaluate", "example-opportunity"],
    ["ingest-url", "https://example.com/job"],
    ["evals", "--no-emit-logfire"],
]


@pytest.mark.parametrize("command", PUBLIC_AI_COMMANDS)
def test_public_ai_cli_commands_never_construct_live_adapter_in_mock_mode(
    command: list[str],
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CAREER_FORGE_MODE", "mock")
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))
    get_settings.cache_clear()

    def reject_live_construction(*args: object, **kwargs: object) -> None:
        raise AssertionError("mock mode constructed the live AI adapter")

    monkeypatch.setattr(PydanticAIService, "__init__", reject_live_construction)
    try:
        result = CliRunner().invoke(app, command)
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0, result.exception


@pytest.mark.parametrize(
    ("command", "execution_owner", "execution_method"),
    [
        (["evaluate", "example-opportunity"], PydanticAIService, "evaluate"),
        (["ingest-url", "https://example.com/job"], JobIngestionPipeline, "ingest_url"),
        (["evals", "--no-emit-logfire"], LogfireEvalRunner, "run_all"),
    ],
)
def test_public_ai_cli_commands_reject_unconfigured_real_mode_before_execution(
    command: list[str],
    execution_owner: type[object],
    execution_method: str,
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("CAREER_FORGE_MODE", "real")
    monkeypatch.setenv("CAREER_FORGE_PYDANTIC_AI_MODEL", "openai:gpt-5.2")
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))
    for name in (
        "CAREER_FORGE_OPENAI_API_KEY",
        "CAREER_OPS_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
        "PYDANTIC_AI_GATEWAY_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()

    def reject_execution(*args: object, **kwargs: object) -> None:
        raise AssertionError("command execution started before configuration validation")

    monkeypatch.setattr(execution_owner, execution_method, reject_execution)
    try:
        result = CliRunner().invoke(app, command)
    finally:
        get_settings.cache_clear()

    assert isinstance(result.exception, AIConfigurationError)


def test_phase3_cli_commands_run_in_safe_dry_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREER_FORGE_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))
    monkeypatch.setenv(
        "CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        str(tmp_path / "missing_credentials.json"),
    )
    monkeypatch.setenv("CAREER_FORGE_GMAIL_TOKEN_PATH", str(tmp_path / "missing_token.json"))
    get_settings.cache_clear()

    runner = CliRunner()

    assert runner.invoke(app, ["ingest-gmail", "--dry-run"]).exit_code == 0
    assert runner.invoke(app, ["sync-notion", "--dry-run"]).exit_code == 0
    assert runner.invoke(app, ["ingest-gmail-message", "--help"]).exit_code == 0
    assert runner.invoke(app, ["events"]).exit_code == 0
    assert runner.invoke(app, ["evaluate", "example-opportunity"]).exit_code == 0
    assert runner.invoke(app, ["feedback"]).exit_code == 0
    assert runner.invoke(app, ["evals", "--no-emit-logfire"]).exit_code == 0
    assert runner.invoke(app, ["logfire-sync", "--no-emit-logfire"]).exit_code == 0
    get_settings.cache_clear()


def test_feedback_cli_records_outcomes_and_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))

    runner = CliRunner()

    assert (
        runner.invoke(
            app, ["record-outcome", "app_1", "interview", "--source", "Recruiter"]
        ).exit_code
        == 0
    )
    assert (
        runner.invoke(
            app,
            [
                "record-override",
                "msg_1",
                "Company Communication",
                "Recruiter Outreach",
                "--prompt-version",
                "email-classifier-v1",
            ],
        ).exit_code
        == 0
    )
    result = runner.invoke(app, ["feedback"])

    assert result.exit_code == 0
    assert "Career Forge Feedback Loop" in result.stdout
