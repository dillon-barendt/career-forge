from datetime import date, timedelta

from career_ops.notion.schemas import Application, ApplicationStatus, JobOpportunity
from career_ops.workflows.apply_queue import ready_to_apply
from career_ops.workflows.followups import due_followups


def test_ready_to_apply_filters_by_score_and_status() -> None:
    strong = JobOpportunity(
        title="Senior Backend Engineer",
        company="Acme",
        description="Python FastAPI Postgres remote observability",
    )
    closed = strong.model_copy(update={"status": ApplicationStatus.CLOSED})

    assert ready_to_apply([strong, closed]) == [strong]


def test_due_followups_excludes_closed_applications() -> None:
    today = date(2026, 7, 7)
    due = Application(
        opportunity_title="Backend Engineer",
        company="Acme",
        status=ApplicationStatus.APPLIED,
        follow_up_on=today - timedelta(days=1),
    )
    closed = due.model_copy(update={"status": ApplicationStatus.CLOSED})

    assert due_followups([due, closed], today=today) == [due]
