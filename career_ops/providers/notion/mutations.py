from career_ops.models import GmailIngestionPlan, JobIngestionResult, NotionMutation


class NotionMutationPlanner:
    """Convert normalized automation results into idempotent Notion write intents."""

    def from_gmail_plan(self, plan: GmailIngestionPlan) -> list[NotionMutation]:
        if not plan.should_mutate_notion:
            return []

        mutations: list[NotionMutation] = []
        source_message_id = plan.dedupe_key.removeprefix("gmail:")
        requires_review = plan.classification.requires_human_review
        safety_notes = ["Low-confidence classification requires review."] if requires_review else []
        if plan.company is not None:
            mutations.append(
                NotionMutation(
                    database="companies",
                    dedupe_key=f"company:{plan.company.name.lower()}",
                    action="upsert",
                    properties={"Name": plan.company.name},
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        if plan.contact is not None:
            mutations.append(
                NotionMutation(
                    database="contacts",
                    dedupe_key=f"contact:{plan.contact.email or plan.contact.name.lower()}",
                    action="upsert",
                    properties={
                        "Name": plan.contact.name,
                        "Email": plan.contact.email or "",
                        "Company": plan.contact.company or "",
                    },
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        if plan.opportunity is not None:
            mutations.append(
                NotionMutation(
                    database="opportunities",
                    dedupe_key=plan.dedupe_key,
                    action="upsert",
                    properties={
                        "Title": plan.opportunity.title,
                        "Company": plan.opportunity.company,
                        "Source": "gmail",
                    },
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        if plan.application is not None:
            mutations.append(
                NotionMutation(
                    database="applications",
                    dedupe_key=f"application:{plan.dedupe_key}",
                    action="upsert",
                    properties={
                        "Opportunity": plan.application.opportunity_title,
                        "Company": plan.application.company,
                        "Status": plan.application.status.value,
                        "Next Action": plan.application.next_action or "",
                    },
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        if plan.interview is not None:
            mutations.append(
                NotionMutation(
                    database="interviews",
                    dedupe_key=f"interview:{plan.dedupe_key}",
                    action="upsert",
                    properties={
                        "Title": plan.interview.title,
                        "Company": plan.interview.company,
                        "Status": plan.interview.status,
                    },
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        if plan.follow_up is not None:
            mutations.append(
                NotionMutation(
                    database="followups",
                    dedupe_key=f"followup:{plan.dedupe_key}",
                    action="upsert",
                    properties={
                        "Title": plan.follow_up.title,
                        "Due": plan.follow_up.due_on.isoformat()
                        if plan.follow_up.due_on is not None
                        else "",
                        "Priority": plan.follow_up.priority,
                    },
                    requires_review=requires_review,
                    source_message_id=source_message_id,
                    safety_notes=safety_notes,
                )
            )
        return mutations

    def from_job_ingestion(self, result: JobIngestionResult) -> list[NotionMutation]:
        return [
            NotionMutation(
                database="companies",
                dedupe_key=f"company:{result.posting.company.lower()}",
                action="upsert",
                properties={"Name": result.posting.company},
            ),
            NotionMutation(
                database="opportunities",
                dedupe_key=f"job:{result.posting.source_url}",
                action="upsert",
                properties={
                    "Title": result.opportunity.title,
                    "Company": result.opportunity.company,
                    "URL": str(result.posting.apply_url or result.posting.source_url),
                    "Fit Score": result.evaluation.fit_score,
                    "Priority": result.recommended_priority,
                    "Next Action": result.recommended_next_action,
                    "AI Summary": result.evaluation.executive_summary,
                },
            ),
        ]
