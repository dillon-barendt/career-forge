from career_ops.notion.schemas import JobOpportunity, MaterialDraft


def build_interview_prep(opportunity: JobOpportunity) -> MaterialDraft:
    body = "\n".join(
        [
            f"# Interview prep for {opportunity.title} at {opportunity.company}",
            "",
            "## Company and role",
            "- Summarize the product, customer, business model, and team charter.",
            "- Map the job description to concrete projects from your background.",
            "",
            "## Stories to prepare",
            "- A high-impact backend system or automation project.",
            "- A debugging or incident story with clear root-cause analysis.",
            "- A cross-functional delivery story with measurable outcome.",
            "",
            "## Questions to ask",
            "- What would success look like in the first 90 days?",
            "- What systems or workflows most need improvement?",
            "- How does the team evaluate engineering quality?",
        ]
    )
    return MaterialDraft(
        opportunity_title=opportunity.title,
        company=opportunity.company,
        kind="interview_prep",
        body=body,
    )
