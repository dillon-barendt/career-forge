from typing import Protocol

from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)


class EmailClassificationService(Protocol):
    """Classifies career inbox messages into typed workflow decisions."""

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation: ...


class OpportunityEvaluationService(Protocol):
    """Evaluates normalized job postings without owning provider I/O."""

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation: ...
