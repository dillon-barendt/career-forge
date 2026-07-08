from career_ops.ai.pydantic_ai_service import PydanticAIService
from career_ops.models import JobPosting, OpportunityEvaluation


class OpportunityEvaluator:
    """Backward-compatible wrapper around the Pydantic AI evaluation service."""

    def __init__(self, ai_service: PydanticAIService | None = None) -> None:
        self.ai_service = ai_service or PydanticAIService()

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        return self.ai_service.evaluate_opportunity(posting)
