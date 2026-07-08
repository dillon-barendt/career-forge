from career_ops.cli import app
from career_ops.config import get_settings
from career_ops.events.log import EventLog
from career_ops.models import EventStatus, EventType, NotionMutation
from typer.testing import CliRunner


def test_phase8_cli_acceptance_commands_run_in_safe_modes(tmp_path, monkeypatch) -> None:
    event_log_path = tmp_path / "events.jsonl"
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(event_log_path))
    monkeypatch.setenv("CAREER_FORGE_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv(
        "CAREER_FORGE_GMAIL_CREDENTIALS_PATH",
        str(tmp_path / "missing_credentials.json"),
    )
    monkeypatch.setenv("CAREER_FORGE_GMAIL_TOKEN_PATH", str(tmp_path / "missing_token.json"))
    get_settings.cache_clear()

    mutation = NotionMutation(
        database="companies",
        dedupe_key="company:acme",
        action="upsert",
        properties={"Name": "Acme"},
    )
    EventLog(event_log_path).append(
        event_type=EventType.NOTION_MUTATION_PLANNED,
        source="notion",
        source_id=mutation.dedupe_key,
        data={"mutation": mutation.model_dump(mode="json")},
        status=EventStatus.PLANNED,
        replay_eligible=True,
    )

    runner = CliRunner()
    try:
        assert runner.invoke(app, ["setup", "validate"]).exit_code == 0
        assert runner.invoke(app, ["ingest-gmail", "--dry-run"]).exit_code == 0
        assert runner.invoke(app, ["notion", "plan", "--latest"]).exit_code == 0
        assert runner.invoke(app, ["notion", "apply", "--latest", "--dry-run"]).exit_code == 0
        assert runner.invoke(app, ["run-once", "--dry-run"]).exit_code == 0
    finally:
        get_settings.cache_clear()
