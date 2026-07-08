from career_ops.analytics.feedback_loop import build_feedback_loop_report
from career_ops.events.log import EventLog
from career_ops.models import EventType


def test_feedback_loop_reports_confidence_sources_and_alerts(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    for index, confidence in enumerate([0.41, 0.52, 0.91], start=1):
        log.append(
            event_type=EventType.EMAIL_CLASSIFIED,
            source="gmail",
            source_id=f"msg_{index}",
            data={
                "confidence": confidence,
                "category": "Recruiter Outreach",
                "prompt_version": "email-classifier-v1",
                "requires_human_review": confidence < 0.65,
            },
        )
    log.append(
        event_type=EventType.HUMAN_OVERRIDE_RECORDED,
        source="human",
        source_id="msg_1",
        data={
            "original": "Recruiter Outreach",
            "corrected": "Newsletter",
            "prompt_version": "email-classifier-v1",
        },
    )
    for outcome in ["applied", "response", "interview"]:
        log.append(
            event_type=EventType.APPLICATION_OUTCOME_RECORDED,
            source="LinkedIn",
            source_id=f"app_{outcome}",
            data={"outcome": outcome, "source": "LinkedIn"},
        )
    log.append(
        event_type=EventType.ERROR_RETRY,
        source="notion",
        source_id="gmail:msg_1",
        data={"error": "rate limited"},
    )

    report = build_feedback_loop_report(log.read_all())

    assert report.metrics["email_classifications"] == 3
    assert report.metrics["low_confidence_rate"] == 0.667
    assert report.application_outcomes["interview"] == 1
    assert report.prompt_performance[0].override_count == 1
    assert report.source_quality[0].source == "LinkedIn"
    assert {alert.name for alert in report.alerts} >= {
        "low_confidence_ingestion_spike",
        "notion_mutation_failures",
    }


def test_feedback_loop_detects_scoring_drift(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    for index, score in enumerate([82, 81, 84, 79, 83, 42, 41, 39, 40, 38], start=1):
        log.append(
            event_type=EventType.AI_EVALUATION_COMPLETED,
            source="lever",
            source_id=f"job_{index}",
            data={
                "fit_score": score,
                "confidence_score": 85,
                "prompt_version": "opportunity-evaluator-v1",
                "recommendation_type": "apply",
            },
        )

    report = build_feedback_loop_report(log.read_all())

    assert "opportunity_scoring_drift" in {alert.name for alert in report.alerts}
