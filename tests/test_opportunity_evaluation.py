from career_ops.evaluation.opportunity import OpportunityEvaluator
from career_ops.models import JobPosting


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
