from career_ops.ai.contracts import OpportunityEvaluationService
from career_ops.ai.factory import build_ai_service
from career_ops.models import JobPosting, OpportunityEvaluation


class OpportunityEvaluator:
    """Evaluates opportunities through the configured provider-agnostic service."""

    def __init__(self, ai_service: OpportunityEvaluationService | None = None) -> None:
        self.ai_service = ai_service if ai_service is not None else build_ai_service()

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        return self.ai_service.evaluate(posting)
