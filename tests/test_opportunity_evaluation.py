from career_ops.evaluation.opportunity import OpportunityEvaluator
from career_ops.models import JobPosting, OpportunityEvaluation


def test_evaluator_produces_structured_reasoning() -> None:
    posting = JobPosting(
        source_url="https://jobs.ashbyhq.com/acme/backend",
        provider="ashby",
        company="Acme",
        role="Senior Backend Engineer",
        location="Remote",
        compensation="$160,000 - $200,000",
        employment_type="Full-time",
        remote_policy="Remote",
        description="Python FastAPI Postgres observability distributed systems",
        skills=["Python", "FastAPI", "Postgres"],
        tech_stack=["Python", "Postgres"],
        apply_url="https://jobs.ashbyhq.com/acme/backend",
    )

    evaluation = OpportunityEvaluator().evaluate(posting)

    assert evaluation.executive_summary.startswith("Senior Backend Engineer")
    assert evaluation.fit_score >= 75
    assert evaluation.confidence_score >= 70
    assert evaluation.suggested_next_action == "prioritize"
    assert evaluation.resume_suggestions
    assert evaluation.cover_letter_talking_points
    assert evaluation.interview_preparation_topics


def test_evaluator_accepts_provider_agnostic_evaluation_service() -> None:
    posting = JobPosting(
        source_url="https://jobs.example.com/acme/backend",
        provider="example",
        company="Acme",
        role="Backend Engineer",
        description="Python services",
        apply_url="https://jobs.example.com/acme/backend",
    )
    expected = OpportunityEvaluation(
        executive_summary="Injected evaluation.",
        fit_score=80,
        confidence_score=90,
        match_analysis="Strong match.",
        suggested_next_action="prioritize",
    )

    class ProviderAgnosticEvaluator:
        def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
            return expected

    result = OpportunityEvaluator(ai_service=ProviderAgnosticEvaluator()).evaluate(posting)

    assert result is expected
