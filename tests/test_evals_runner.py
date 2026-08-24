from pathlib import Path

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.evals.runner import LogfireEvalRunner
from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)


class ProviderAgnosticAIService:
    """Delegates typed eval decisions without exposing provider properties."""

    def __init__(self) -> None:
        self._delegate = DeterministicAIService()

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        return self._delegate.classify_email(message)

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        return self._delegate.evaluate(posting)


def test_eval_runner_uses_protocol_methods_and_explicit_reporting_metadata() -> None:
    runner = LogfireEvalRunner(
        evals_dir=Path("evals"),
        ai_service=ProviderAgnosticAIService(),
        model_route="mock:test-route",
    )

    summaries = runner.run_all()

    assert len(summaries) == 2
    assert all(summary.model_route == "mock:test-route" for summary in summaries)
