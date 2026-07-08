from career_ops.notion.schemas import ApplicationStatus, JobOpportunity
from career_ops.scoring.fit_score import score_opportunity


def ready_to_apply(
    opportunities: list[JobOpportunity],
    minimum_score: int = 75,
) -> list[JobOpportunity]:
    return [
        opportunity
        for opportunity in opportunities
        if opportunity.status in {ApplicationStatus.NEW, ApplicationStatus.REVIEWING}
        and score_opportunity(opportunity).score >= minimum_score
    ]
