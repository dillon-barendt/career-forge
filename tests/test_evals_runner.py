from pathlib import Path

import pytest

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.config import Settings
from career_ops.evals.runner import LogfireEvalRunner
from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)
from career_ops.observability import Observability


class ProviderAgnosticAIService:
    """Delegates typed eval decisions without exposing provider properties."""

    def __init__(self) -> None:
        self._delegate = DeterministicAIService()

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        return self._delegate.classify_email(message)

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        return self._delegate.evaluate(posting)


class GatewayOverrideObservability(Observability):
    """Supplies a deterministic Logfire gateway override for routing tests."""

    def __init__(self, settings: Settings, *, enabled: bool) -> None:
        super().__init__(settings)
        self.enabled = enabled
        self.resolve_calls = 0

    def resolve_bool(self, name: str, default: bool, **context: str) -> bool:
        assert name == "career_forge.ai.gateway_enabled"
        assert default is self.settings.pydantic_ai_gateway_enabled
        assert context == {"targeting_key": "career-forge"}
        self.resolve_calls += 1
        return self.enabled


def test_eval_runner_uses_protocol_methods_and_explicit_reporting_metadata() -> None:
    runner = LogfireEvalRunner(
        evals_dir=Path("evals"),
        ai_service=ProviderAgnosticAIService(),
        model_route="mock:test-route",
    )

    summaries = runner.run_all()

    assert len(summaries) == 2
    assert all(summary.model_route == "mock:test-route" for summary in summaries)


@pytest.mark.parametrize(
    ("configured_gateway", "effective_gateway", "openai_key", "gateway_key", "route"),
    [
        (False, True, None, "pylf-test", "gateway/openai:gpt-5.2"),
        (True, False, "sk-test", None, "openai:gpt-5.2"),
    ],
)
def test_default_eval_runner_reports_same_route_used_by_logfire_override(
    monkeypatch,
    configured_gateway: bool,
    effective_gateway: bool,
    openai_key: str | None,
    gateway_key: str | None,
    route: str,
) -> None:
    settings = Settings(
        _env_file=None,
        mode="real",
        pydantic_ai_model="openai:gpt-5.2",
        pydantic_ai_gateway_enabled=configured_gateway,
        pydantic_ai_gateway_api_key=gateway_key,
        openai_api_key=openai_key,
    )
    observability = GatewayOverrideObservability(settings, enabled=effective_gateway)
    monkeypatch.setattr("career_ops.evals.runner.get_settings", lambda: settings)

    runner = LogfireEvalRunner(observability=observability)

    assert isinstance(runner.ai_service, PydanticAIService)
    assert runner.model_route == runner.ai_service._agent_model_name() == route
    assert observability.resolve_calls == 1
