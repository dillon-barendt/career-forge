from collections.abc import Mapping

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)

EmailMockResult = PydanticAIEmailEvaluation | Exception
OpportunityMockResult = OpportunityEvaluation | Exception


class MockAIService:
    """Returns deterministic or test-controlled typed AI decisions without I/O."""

    model = "mock:deterministic-v1"

    def __init__(
        self,
        *,
        email_results: Mapping[str, EmailMockResult] | None = None,
        opportunity_results: Mapping[str, OpportunityMockResult] | None = None,
        fallback: DeterministicAIService | None = None,
    ) -> None:
        self.email_results = dict(email_results or {})
        self.opportunity_results = dict(opportunity_results or {})
        self.fallback = fallback if fallback is not None else DeterministicAIService()

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        result = self.email_results.get(message.message_id)
        if isinstance(result, Exception):
            raise result
        if result is not None:
            return result.model_copy(update={"model_name": self.model, "fallback_status": "mock"})
        return self.fallback.classify_email(message).model_copy(
            update={"model_name": self.model, "fallback_status": "mock"}
        )

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        result = self.opportunity_results.get(str(posting.source_url))
        if isinstance(result, Exception):
            raise result
        return result if result is not None else self.fallback.evaluate(posting)
