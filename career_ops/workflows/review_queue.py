from career_ops.notion.schemas import FitScore, JobOpportunity
from career_ops.scoring.fit_score import score_opportunity


def review_opportunities(
    opportunities: list[JobOpportunity],
) -> list[tuple[JobOpportunity, FitScore]]:
    scored = [(opportunity, score_opportunity(opportunity)) for opportunity in opportunities]
    return sorted(scored, key=lambda item: item[1].score, reverse=True)
