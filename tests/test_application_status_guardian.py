import json
from datetime import date

from career_ops.events.log import EventLog
from career_ops.models import EventStatus, EventType
from career_ops.workflows.application_status_guardian import (
    GuardianApplication,
    build_application_status_health_report,
    load_guardian_applications,
)


def test_guardian_flags_stale_missing_data_and_conflicts(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl")
    event_log.append(
        event_type=EventType.APPLICATION_OUTCOME_RECORDED,
        source="manual",
        source_id="app_1",
        data={"outcome": "rejection"},
    )

    report = build_application_status_health_report(
        [
            GuardianApplication(
                application_id="app_1",
                opportunity_title="Backend Engineer",
                company="Acme",
                source="Gmail",
                status="applied",
                applied_on=date(2026, 6, 1),
            ),
            GuardianApplication(
                application_id="app_2",
                opportunity_title="Platform Engineer",
                company="",
                source=None,
                status="new",
            ),
            GuardianApplication(
                application_id="app_3",
                opportunity_title="Staff Engineer",
                company="Beta",
                source="LinkedIn",
                status="closed",
                follow_up_on=date(2026, 7, 7),
            ),
        ],
        report_date=date(2026, 7, 8),
        events=event_log.read_all(),
    )

    assert report.applications_checked == 3
    assert report.stale_count == 2
    assert report.missing_data_count == 1
    assert report.status_conflict_count == 2
    assert report.review_required_count == 5
    assert all(finding.requires_human_review for finding in report.findings)


def test_load_guardian_applications_accepts_wrapped_json(tmp_path) -> None:
    path = tmp_path / "applications.json"
    path.write_text(
        json.dumps(
            {
                "applications": [
                    {
                        "application_id": "app_1",
                        "opportunity_title": "Backend Engineer",
                        "company": "Acme",
                        "source": "Gmail",
                        "status": "applied",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    applications = load_guardian_applications(path)

    assert applications[0].application_id == "app_1"
    assert applications[0].company == "Acme"


def test_guardian_report_events_keep_status_changes_human_reviewed(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl")
    report = build_application_status_health_report(
        [
            GuardianApplication(
                application_id="app_1",
                opportunity_title="Backend Engineer",
                company="Acme",
                source="Gmail",
                status="applied",
                applied_on=date(2026, 7, 8),
                status_signals=["offer"],
            )
        ],
        report_date=date(2026, 7, 8),
    )
    summary = event_log.append(
        event_type=EventType.APPLICATION_STATUS_HEALTH_REPORTED,
        source="application_status_guardian",
        source_id=report.report_date.isoformat(),
        data={"findings_total": len(report.findings)},
        status=EventStatus.REVIEW_REQUIRED,
    )
    for finding in report.findings:
        event_log.append(
            event_type=EventType.HUMAN_REVIEW_REQUIRED,
            source="application_status_guardian",
            source_id=finding.application_id,
            data=finding.model_dump(mode="json"),
            correlation_id=summary.event_id,
            status=EventStatus.REVIEW_REQUIRED,
        )

    events = event_log.read_all()

    assert [event.event_type for event in events] == [
        EventType.APPLICATION_STATUS_HEALTH_REPORTED,
        EventType.HUMAN_REVIEW_REQUIRED,
    ]
    assert events[1].data["kind"] == "status_conflict"
    assert events[1].data["requires_human_review"] is True
