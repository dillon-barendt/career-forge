from career_ops.cli import app
from typer.testing import CliRunner


def test_phase3_cli_commands_run_in_safe_dry_mode(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREER_OPS_STATE_PATH", str(tmp_path / "state.json"))
    monkeypatch.setenv("CAREER_OPS_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))

    runner = CliRunner()

    assert runner.invoke(app, ["ingest-gmail", "--dry-run"]).exit_code == 0
    assert runner.invoke(app, ["sync-notion", "--dry-run"]).exit_code == 0
    assert runner.invoke(app, ["events"]).exit_code == 0
    assert runner.invoke(app, ["evaluate", "example-opportunity"]).exit_code == 0
    assert runner.invoke(app, ["feedback"]).exit_code == 0


def test_feedback_cli_records_outcomes_and_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CAREER_OPS_EVENT_LOG_PATH", str(tmp_path / "events.jsonl"))

    runner = CliRunner()

    assert (
        runner.invoke(app, ["record-outcome", "app_1", "interview", "--source", "Recruiter"])
        .exit_code
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
    assert "Career Ops Feedback Loop" in result.stdout
