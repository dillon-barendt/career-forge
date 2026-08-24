from career_ops.ai.deterministic import DeterministicAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.models import EmailCategory, EmailMessage, JobPosting


def _email(subject: str, body: str) -> EmailMessage:
    return EmailMessage(
        message_id="msg-demo",
        thread_id="thread-demo",
        sender="Avery Recruiter <avery@acme.com>",
        recipients=["candidate@example.com"],
        subject=subject,
        body=body,
        received_at="2026-08-24T12:00:00Z",
    )


def test_deterministic_service_classifies_interview_invitation() -> None:
    result = DeterministicAIService().classify_email(
        _email(
            "Interview invitation for Platform Engineer at Acme",
            "Please send your availability for a technical interview.",
        )
    )

    assert result.classification == EmailCategory.INTERVIEW_INVITATION
    assert result.confidence_score == 0.9
    assert result.human_review_required is False
    assert result.model_name == "deterministic:rules-v1"
    assert result.fallback_status == "deterministic"


def test_deterministic_service_handles_offer_and_follow_up_signals() -> None:
    service = DeterministicAIService()

    offer = service.classify_email(
        _email("Your offer letter", "We are pleased to send the attached offer letter.")
    )
    follow_up = service.classify_email(
        _email("Following up", "I am circling back about the platform role.")
    )

    assert offer.classification == EmailCategory.OFFER
    assert follow_up.classification == EmailCategory.RECRUITER_FOLLOW_UP


def test_deterministic_service_evaluates_typed_opportunity() -> None:
    posting = JobPosting(
        source_url="https://jobs.ashbyhq.com/acme/platform",
        provider="ashby",
        company="Acme",
        role="Principal Platform Engineer",
        location="Remote",
        compensation="$190,000 - $230,000",
        remote_policy="Remote",
        description="Python FastAPI Postgres observability distributed systems automation",
        skills=["Python", "FastAPI", "Postgres"],
        tech_stack=["Python", "Postgres"],
        apply_url="https://jobs.ashbyhq.com/acme/platform",
    )

    result = DeterministicAIService().evaluate(posting)

    assert result.fit_score >= 75
    assert result.confidence_score == 100
    assert result.suggested_next_action == "prioritize"
    assert result.resume_suggestions == ["Mirror the target title: Principal Platform Engineer."]


def test_gmail_pipeline_accepts_deterministic_service_protocol() -> None:
    plan = GmailIngestionPipeline(ai_service=DeterministicAIService()).plan(
        _email(
            "Interview invitation for Platform Engineer at Acme",
            "Please send your availability for a technical interview.",
        )
    )

    assert plan.classification.category == EmailCategory.INTERVIEW_INVITATION
    assert plan.interview is not None
    assert plan.should_mutate_notion is True
