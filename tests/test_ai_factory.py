import os
import sys
from types import ModuleType

import pytest
from pydantic import ValidationError
from tests.fixtures.mock_llm import (
    canned_email_result,
    canned_opportunity_result,
    mock_ai_service,
)

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.ai.factory import AIConfigurationError, build_ai_service
from career_ops.ai.mock import MockAIService
from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.config import RuntimeMode, Settings
from career_ops.models import EmailCategory, EmailMessage, JobPosting


def _email(message_id: str, *, subject: str = "Interview invitation") -> EmailMessage:
    return EmailMessage(
        message_id=message_id,
        thread_id="thread-1",
        sender="Recruiter <recruiter@acme.example>",
        recipients=["candidate@example.com"],
        subject=subject,
        body="Please send your availability for a technical interview.",
        received_at="2026-08-24T12:00:00Z",
    )


def _posting(source_url: str = "https://jobs.example.com/acme/platform") -> JobPosting:
    return JobPosting(
        source_url=source_url,
        provider="example",
        company="Acme",
        role="Platform Engineer",
        location="Remote",
        compensation="$180,000 - $220,000",
        remote_policy="Remote",
        description="Python distributed systems platform engineering",
        skills=["Python"],
        tech_stack=["Python"],
        apply_url=source_url,
    )


def test_settings_default_to_mock_mode() -> None:
    assert Settings(_env_file=None).mode is RuntimeMode.MOCK


def test_settings_reject_unknown_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mode="automatic")


def test_factory_builds_mock_without_credentials() -> None:
    service = build_ai_service(Settings(_env_file=None, mode="mock"))

    assert isinstance(service, MockAIService)


def test_real_openai_mode_requires_credentials() -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        openai_api_key=None,
    )

    with pytest.raises(AIConfigurationError, match="CAREER_FORGE_OPENAI_API_KEY"):
        build_ai_service(settings)


@pytest.mark.parametrize("openai_api_key", ["", "   "])
def test_real_openai_mode_rejects_blank_credentials(openai_api_key: str) -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        openai_api_key=openai_api_key,
    )

    with pytest.raises(AIConfigurationError, match="CAREER_FORGE_OPENAI_API_KEY"):
        build_ai_service(settings)


def test_real_gateway_mode_requires_gateway_credentials() -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        pydantic_ai_gateway_enabled=True,
        pydantic_ai_gateway_api_key=None,
        openai_api_key=None,
    )

    with pytest.raises(
        AIConfigurationError,
        match="CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
    ):
        build_ai_service(settings)


@pytest.mark.parametrize("gateway_api_key", ["", "   "])
def test_real_gateway_mode_rejects_blank_credentials(gateway_api_key: str) -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        pydantic_ai_gateway_enabled=True,
        pydantic_ai_gateway_api_key=gateway_api_key,
        openai_api_key=None,
    )

    with pytest.raises(
        AIConfigurationError,
        match="CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY",
    ):
        build_ai_service(settings)


def test_real_gateway_mode_builds_provider_with_gateway_credentials() -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        pydantic_ai_gateway_enabled=True,
        pydantic_ai_gateway_api_key="pylf-test",
        openai_api_key=None,
    )

    service = build_ai_service(settings)

    assert isinstance(service, PydanticAIService)
    assert service.model == "openai:gpt-5.2"
    assert service.allow_local_fallback is False


def test_factory_passes_explicit_settings_to_provider_construction(monkeypatch) -> None:
    for name in (
        "CAREER_FORGE_OPENAI_API_KEY",
        "CAREER_OPS_OPENAI_API_KEY",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-explicit",
        openai_api_key="sk-explicit",
    )
    fake_module = ModuleType("pydantic_ai")

    class FakeAgent:
        def __init__(self, model: object, *args: object, **kwargs: object) -> None:
            assert model == "openai:gpt-explicit"
            assert os.environ["OPENAI_API_KEY"] == "sk-explicit"

        def run_sync(self, prompt: str) -> object:
            raise AssertionError("agent execution is outside this construction test")

    fake_module.Agent = FakeAgent
    monkeypatch.setitem(sys.modules, "pydantic_ai", fake_module)

    service = build_ai_service(settings)
    agent = service._build_agent(
        output_type=object,
        name="explicit_settings",
        instructions="test",
    )

    assert isinstance(agent, FakeAgent)


def test_mock_returns_configured_email_result_with_mock_metadata() -> None:
    configured = canned_email_result()
    service = MockAIService(email_results={"msg-configured": configured})

    result = service.classify_email(_email("msg-configured"))

    assert result.classification is EmailCategory.INTERVIEW_INVITATION
    assert result.confidence_score == 0.93
    assert result.model_name == "mock:deterministic-v1"
    assert result.fallback_status == "mock"


def test_mock_propagates_configured_email_failure() -> None:
    service = MockAIService(email_results={"msg-failure": RuntimeError("provider unavailable")})

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.classify_email(_email("msg-failure"))


def test_mock_delegates_unconfigured_email_to_deterministic_rules() -> None:
    result = mock_ai_service().classify_email(_email("msg-unconfigured"))

    assert result.classification is EmailCategory.INTERVIEW_INVITATION
    assert result.confidence_score == 0.9
    assert result.model_name == "mock:deterministic-v1"
    assert result.fallback_status == "mock"


def test_mock_preserves_explicitly_injected_falsey_fallback() -> None:
    class FalseyFallback(DeterministicAIService):
        def __bool__(self) -> bool:
            return False

        def classify_email(self, message: EmailMessage):
            return canned_email_result()

    result = MockAIService(fallback=FalseyFallback()).classify_email(_email("msg-fallback"))

    assert result.confidence_score == 0.93
    assert result.model_name == "mock:deterministic-v1"
    assert result.fallback_status == "mock"


def test_mock_returns_configured_opportunity_result() -> None:
    posting = _posting()
    configured = canned_opportunity_result()
    service = MockAIService(opportunity_results={str(posting.source_url): configured})

    result = service.evaluate(posting)

    assert result is configured
    assert result.fit_score == 91


def test_mock_propagates_configured_opportunity_failure() -> None:
    posting = _posting()
    service = MockAIService(
        opportunity_results={str(posting.source_url): RuntimeError("provider unavailable")}
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        service.evaluate(posting)


def test_mock_delegates_unconfigured_opportunity_to_deterministic_rules() -> None:
    result = mock_ai_service().evaluate(_posting())

    assert result.fit_score == 69
    assert result.suggested_next_action == "review"
