from career_ops.notion.schemas import JobOpportunity, MaterialDraft


def build_recruiter_dm(
    opportunity: JobOpportunity,
    contact_name: str | None = None,
) -> MaterialDraft:
    greeting = f"Hi {contact_name}," if contact_name else "Hi,"
    body = "\n".join(
        [
            greeting,
            "",
            f"I saw the {opportunity.title} role at {opportunity.company} and wanted to reach out. "
            "My background is in Python backend engineering, API development, automation, and "
            "shipping practical tools that improve operational workflows.",
            "",
            "If the team is still reviewing candidates, I would appreciate the chance to connect.",
            "",
            "Best,",
            "Dillon",
        ]
    )
    return MaterialDraft(
        opportunity_title=opportunity.title,
        company=opportunity.company,
        kind="recruiter_dm",
        body=body,
    )
