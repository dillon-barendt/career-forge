from career_ops.notion.schemas import JobOpportunity
from career_ops.scoring.fit_score import score_opportunity


def test_python_backend_role_is_prioritized() -> None:
    opportunity = JobOpportunity(
        title="Senior Backend Engineer",
        company="Acme",
        description="Python FastAPI Postgres observability remote distributed systems",
    )

    result = score_opportunity(opportunity)

    assert result.score >= 75
    assert result.recommended_action == "prioritize"
    assert result.strengths


def test_clear_mismatch_is_deprioritized() -> None:
    opportunity = JobOpportunity(
        title="Onsite Java Only Engineer",
        company="Acme",
        description="Requires clearance. Unpaid trial period.",
    )

    result = score_opportunity(opportunity)

    assert result.score < 55
    assert result.recommended_action == "deprioritize"
    assert result.concerns
