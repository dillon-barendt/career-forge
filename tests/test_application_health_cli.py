import json

from career_ops.cli import app
from career_ops.config import get_settings
from career_ops.events.log import EventLog
from career_ops.models import EventType
from typer.testing import CliRunner


def test_application_health_cli_emits_report_and_review_events(tmp_path, monkeypatch) -> None:
    event_log_path = tmp_path / "events.jsonl"
    applications_path = tmp_path / "applications.json"
    applications_path.write_text(
        json.dumps(
            [
                {
                    "application_id": "app_1",
                    "opportunity_title": "Backend Engineer",
                    "company": "Acme",
                    "source": "Gmail",
                    "status": "applied",
                    "applied_on": "2026-06-01",
                    "status_signals": ["offer"],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(event_log_path))
    get_settings.cache_clear()

    try:
        result = CliRunner().invoke(
            app,
            [
                "application-health",
                str(applications_path),
                "--report-date",
                "2026-07-08",
            ],
        )
    finally:
        get_settings.cache_clear()

    assert result.exit_code == 0
    assert "Application Status Guardian" in result.output
    events = EventLog(event_log_path).read_all()
    assert events[0].event_type == EventType.APPLICATION_STATUS_HEALTH_REPORTED
    assert events[0].data["stale_applications"] == 1
    assert events[0].data["status_conflicts"] == 1
    assert [event.event_type for event in events[1:]] == [
        EventType.HUMAN_REVIEW_REQUIRED,
        EventType.HUMAN_REVIEW_REQUIRED,
    ]


def test_stale_and_review_commands_read_event_log(tmp_path, monkeypatch) -> None:
    event_log_path = tmp_path / "events.jsonl"
    EventLog(event_log_path).append(
        event_type=EventType.HUMAN_REVIEW_REQUIRED,
        source="application_status_guardian",
        source_id="app_1",
        data={
            "kind": "stale_application",
            "detail": "applied has had no activity for 37 days.",
            "recommended_action": "Human-review the status before follow-up.",
        },
    )
    monkeypatch.setenv("CAREER_FORGE_EVENT_LOG_PATH", str(event_log_path))
    get_settings.cache_clear()

    try:
        stale_result = CliRunner().invoke(app, ["stale"])
        review_result = CliRunner().invoke(app, ["review"])
    finally:
        get_settings.cache_clear()

    assert stale_result.exit_code == 0
    assert "app_1" in stale_result.output
    assert "37 days" in stale_result.output
    assert review_result.exit_code == 0
    assert "Human-review the status" in review_result.output
