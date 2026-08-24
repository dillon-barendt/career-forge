from career_ops.ai.mock import MockAIService
from career_ops.models import EmailCategory, OpportunityEvaluation, PydanticAIEmailEvaluation


def canned_email_result() -> PydanticAIEmailEvaluation:
    return PydanticAIEmailEvaluation(
        classification=EmailCategory.INTERVIEW_INVITATION,
        confidence_score=0.93,
        executive_summary="Acme invited the candidate to interview.",
        suggested_next_action="Reply with availability.",
        human_review_required=False,
        reasons=["The message explicitly requests interview availability."],
        prompt_version="email-classifier-v1",
        model_name="openai:test-model",
        fallback_status="none",
    )


def canned_opportunity_result() -> OpportunityEvaluation:
    return OpportunityEvaluation(
        executive_summary="Strong platform engineering opportunity at Acme.",
        fit_score=91,
        confidence_score=96,
        match_analysis="The role aligns with the candidate's platform experience.",
        strengths=["Python", "Distributed systems"],
        potential_concerns=[],
        missing_qualifications=[],
        resume_suggestions=["Emphasize platform reliability impact."],
        cover_letter_talking_points=["Connect prior platform work to Acme's scale."],
        interview_preparation_topics=["Distributed systems tradeoffs"],
        suggested_next_action="prioritize",
    )


def mock_ai_service() -> MockAIService:
    return MockAIService()
