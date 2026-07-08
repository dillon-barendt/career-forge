import os
import sys
from types import ModuleType

from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.config import get_settings
from career_ops.models import EmailCategory, EmailMessage, PydanticAIEmailEvaluation


class FakeEmailAgent:
    def run_sync(self, prompt: str):
        assert "msg_1" in prompt
        return type(
            "AgentResult",
            (),
            {
                "output": PydanticAIEmailEvaluation(
                    classification=EmailCategory.INTERVIEW_INVITATION,
                    confidence_score=0.91,
                    executive_summary="Interview invite from Acme.",
                    suggested_next_action="Reply with availability.",
                    human_review_required=False,
                    reasons=["Scheduling language is explicit."],
                )
            },
        )()


def test_pydantic_ai_service_returns_structured_email_evaluation() -> None:
    message = EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation",
        body="Please send availability for a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )

    result = PydanticAIService(email_agent=FakeEmailAgent()).classify_email(message)

    assert result.classification == EmailCategory.INTERVIEW_INVITATION
    assert result.confidence_score == 0.91
    assert result.prompt_version == "email-classifier-v1"
    assert result.human_review_required is False


def test_pydantic_ai_service_loads_openai_key_from_settings(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CAREER_FORGE_OPENAI_API_KEY", "sk-test-local")
    get_settings.cache_clear()

    fake_module = ModuleType("pydantic_ai")

    class FakeAgent:
        def __init__(self, *args, **kwargs) -> None:
            assert os.environ["OPENAI_API_KEY"] == "sk-test-local"

        def run_sync(self, prompt: str):
            raise AssertionError("Agent should not run in this test")

    fake_module.Agent = FakeAgent
    monkeypatch.setitem(sys.modules, "pydantic_ai", fake_module)

    try:
        agent = PydanticAIService(allow_local_fallback=False)._build_agent(
            output_type=PydanticAIEmailEvaluation,
            name="test_agent",
            instructions="test",
        )
    finally:
        get_settings.cache_clear()

    assert isinstance(agent, FakeAgent)
