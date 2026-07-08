from career_ops.notion.schemas import JobOpportunity, MaterialDraft


def build_cover_letter(opportunity: JobOpportunity) -> MaterialDraft:
    body = "\n".join(
        [
            f"Hi {opportunity.company} team,",
            "",
            f"I am interested in the {opportunity.title} role because it matches my focus on "
            "building reliable software systems, improving product workflows, and delivering "
            "practical engineering outcomes.",
            "",
            "My background is strongest where Python, APIs, data workflows, observability, and "
            "cross-functional execution matter. I would tailor the final version around the "
            "specific role requirements and the highest-signal examples from my recent work.",
            "",
            "Best,",
            "Dillon",
        ]
    )
    return MaterialDraft(
        opportunity_title=opportunity.title,
        company=opportunity.company,
        kind="cover_letter",
        body=body,
    )
