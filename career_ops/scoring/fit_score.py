from career_ops.notion.schemas import FitScore, JobOpportunity
from career_ops.scoring.rules import NEGATIVE_RULES, POSITIVE_RULES, normalize_text


def score_opportunity(opportunity: JobOpportunity) -> FitScore:
    text = normalize_text(
        " ".join(
            [
                opportunity.title,
                opportunity.company,
                opportunity.description,
                opportunity.location or "",
                " ".join(opportunity.tags),
            ]
        )
    )

    score = 45
    strengths: list[str] = []
    concerns: list[str] = []

    for rule in POSITIVE_RULES:
        if rule.keyword in text:
            score += rule.points
            strengths.append(rule.reason)

    for rule in NEGATIVE_RULES:
        if rule.keyword in text:
            score += rule.points
            concerns.append(rule.reason)

    score = max(0, min(100, score))

    if score >= 75:
        action = "prioritize"
    elif score >= 55:
        action = "review"
    else:
        action = "deprioritize"

    return FitScore(
        score=score,
        strengths=strengths,
        concerns=concerns,
        recommended_action=action,
    )
