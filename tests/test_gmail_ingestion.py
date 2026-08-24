import pytest

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.ai.mock import MockAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.models import EmailCategory, EmailMessage


def test_interview_invitation_creates_interview_and_followup_plan() -> None:
    message = EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body=(
            "We would like to schedule a technical interview for the Backend Engineer "
            "role at Acme next week."
        ),
        received_at="2026-07-07T16:00:00Z",
    )

    plan = GmailIngestionPipeline().plan(message)

    assert plan.classification.category == EmailCategory.INTERVIEW_INVITATION
    assert plan.classification.confidence >= 0.8
    assert plan.company is not None
    assert plan.company.name == "Acme"
    assert plan.contact is not None
    assert plan.contact.email == "sam@acme.com"
    assert plan.interview is not None
    assert plan.follow_up is not None
    assert plan.audit_events[0].source_id == "msg_1"


def test_newsletter_is_ignored_without_notion_mutations() -> None:
    message = EmailMessage(
        message_id="msg_2",
        thread_id="thread_2",
        sender="Jobs Digest <digest@example.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Weekly software engineering jobs newsletter",
        body="Here are 100 jobs you may like.",
        received_at="2026-07-07T17:00:00Z",
    )

    plan = GmailIngestionPipeline().plan(message)

    assert plan.classification.category == EmailCategory.NEWSLETTER
    assert plan.should_mutate_notion is False
    assert plan.company is None
    assert plan.follow_up is None


def test_default_pipeline_uses_configured_mock_service() -> None:
    pipeline = GmailIngestionPipeline()

    assert isinstance(pipeline.ai_service, MockAIService)


def test_pipeline_preserves_an_explicit_falsey_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_factory_is_called():
        raise AssertionError("injected Gmail pipeline loaded the AI factory")

    monkeypatch.setattr(
        "career_ops.automation.gmail_ingestion.build_ai_service",
        fail_if_factory_is_called,
    )

    class FalseyDeterministicService(DeterministicAIService):
        def __bool__(self) -> bool:
            return False

    service = FalseyDeterministicService()

    pipeline = GmailIngestionPipeline(ai_service=service)

    assert pipeline.ai_service is service
