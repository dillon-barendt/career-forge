from career_ops.notion.schemas import JobOpportunity, MaterialDraft


def build_resume_tailoring_notes(opportunity: JobOpportunity) -> MaterialDraft:
    body = "\n".join(
        [
            f"# Resume tailoring notes for {opportunity.title} at {opportunity.company}",
            "",
            "## Emphasize",
            "- Python backend systems, API ownership, reliability, and product impact.",
            "- Metrics, scale, latency, cost, revenue, or operational improvements.",
            "- Work that matches the job description language without inventing experience.",
            "",
            "## Pull from job description",
            opportunity.description.strip()
            or "Add role requirements from Notion before tailoring.",
        ]
    )
    return MaterialDraft(
        opportunity_title=opportunity.title,
        company=opportunity.company,
        kind="resume_tailoring",
        body=body,
    )
