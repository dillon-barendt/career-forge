from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.models import (
    ClassifiedGmailMessage,
    EmailCategory,
    EmailMessage,
    GmailClassificationType,
)


class MalformedEmailAgent:
    def run_sync(self, prompt: str):
        return type(
            "AgentResult",
            (),
            {"output": {"classification": "not-a-real-classification", "confidence_score": 2}},
        )()


def _message() -> EmailMessage:
    return EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="Please send availability for a technical interview next week.",
        received_at="2026-07-07T16:00:00Z",
    )


def test_classified_gmail_message_contract_includes_operator_metadata() -> None:
    message = _message()
    plan = GmailIngestionPipeline().plan(message)

    classified = ClassifiedGmailMessage.from_plan(
        message=message,
        plan=plan,
        model_name="openai:gpt-5.2",
        fallback_status="local_fallback",
    )

    assert classified.message_id == "msg_1"
    assert classified.thread_id == "thread_1"
    assert classified.classification_type == GmailClassificationType.INTERVIEW
    assert classified.confidence >= 0.8
    assert classified.recommended_notion_intent == "upsert"
    assert classified.prompt_version == "email-classifier-v1"
    assert classified.model_name == "openai:gpt-5.2"
    assert classified.fallback_status == "local_fallback"
    assert classified.extracted_opportunity_fields["company"] == "Acme"
    assert classified.extracted_company_fields["name"] == "Acme"


def test_malformed_ai_output_uses_structured_fallback() -> None:
    result = PydanticAIService(email_agent=MalformedEmailAgent()).classify_email(_message())

    assert result.classification == EmailCategory.INTERVIEW_INVITATION
    assert result.confidence_score >= 0.8
    assert result.prompt_version == "email-classifier-v1"
    assert result.model_name == "openai:gpt-5.2"
    assert result.fallback_status == "local_fallback"
