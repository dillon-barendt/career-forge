import re
from datetime import timedelta
from email.utils import parseaddr

from career_ops.ai.contracts import EmailClassificationService
from career_ops.ai.factory import build_ai_service
from career_ops.models import (
    AuditEvent,
    EmailCategory,
    EmailClassification,
    EmailMessage,
    FollowUpRecord,
    GmailIngestionPlan,
    InterviewRecord,
)
from career_ops.notion.schemas import (
    Application,
    ApplicationStatus,
    Company,
    Contact,
    JobOpportunity,
)


class GmailIngestionPipeline:
    """Classify Gmail messages and create idempotent Notion mutation plans."""

    def __init__(self, ai_service: EmailClassificationService | None = None) -> None:
        self.ai_service = ai_service if ai_service is not None else build_ai_service()

    def classify(self, message: EmailMessage) -> EmailClassification:
        ai_result = self.ai_service.classify_email(message)
        return EmailClassification(
            category=ai_result.classification,
            confidence=ai_result.confidence_score,
            reasons=ai_result.reasons,
            requires_human_review=ai_result.human_review_required,
            prompt_version=ai_result.prompt_version,
            model_name=ai_result.model_name,
            fallback_status=ai_result.fallback_status,
        )

    def plan(self, message: EmailMessage) -> GmailIngestionPlan:
        classification = self.classify(message)
        dedupe_key = f"gmail:{message.message_id}"
        audit_events = [
            AuditEvent(
                source="gmail",
                source_id=message.message_id,
                action="classified",
                message=(
                    f"Classified as {classification.category.value} "
                    f"with confidence {classification.confidence:.2f}."
                ),
            )
        ]

        if classification.category in {EmailCategory.NEWSLETTER, EmailCategory.IGNORE}:
            return GmailIngestionPlan(
                classification=classification,
                should_mutate_notion=False,
                audit_events=audit_events,
                dedupe_key=dedupe_key,
            )

        company_name = self._extract_company(message)
        role_title = self._extract_role(message)
        contact = self._extract_contact(message, company_name)
        company = Company(name=company_name)
        opportunity = JobOpportunity(
            title=role_title,
            company=company_name,
            description=self._summarize_email(message),
            source="gmail",
        )
        application = Application(
            opportunity_title=role_title,
            company=company_name,
            status=self._application_status(classification.category),
            next_action=self._next_action(classification.category),
        )
        interview = self._build_interview(
            message,
            classification.category,
            company_name,
            role_title,
        )
        follow_up = self._build_follow_up(
            message,
            classification.category,
            company_name,
            role_title,
        )

        return GmailIngestionPlan(
            classification=classification,
            should_mutate_notion=True,
            company=company,
            contact=contact,
            opportunity=opportunity,
            application=application,
            interview=interview,
            follow_up=follow_up,
            audit_events=audit_events,
            dedupe_key=dedupe_key,
        )

    def _extract_contact(self, message: EmailMessage, company_name: str) -> Contact:
        name, email = parseaddr(message.sender)
        if not name:
            name = email.split("@", maxsplit=1)[0].replace(".", " ").title() if email else "Unknown"
        return Contact(name=name, email=email or None, company=company_name, role="Recruiter")

    def _extract_company(self, message: EmailMessage) -> str:
        text = f"{message.subject}\n{message.body}"
        for pattern in (
            r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{1,40})",
            r"\bwith\s+([A-Z][A-Za-z0-9&.\- ]{1,40})",
            r"\bfrom\s+([A-Z][A-Za-z0-9&.\- ]{1,40})",
        ):
            match = re.search(pattern, text)
            if match:
                return self._clean_company(match.group(1))

        _, email = parseaddr(message.sender)
        domain = email.split("@")[-1].split(".")[0] if "@" in email else "Unknown"
        return domain.replace("-", " ").title()

    def _extract_role(self, message: EmailMessage) -> str:
        text = f"{message.subject}\n{message.body}"
        for pattern in (
            r"\bfor\s+(?:the\s+)?([A-Z][A-Za-z0-9 /\-]+(?:Engineer|Developer|Lead|Manager))",
            r"\b([A-Z][A-Za-z0-9 /\-]+(?:Engineer|Developer|Lead|Manager))\b",
        ):
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        return "Software Engineering Opportunity"

    def _clean_company(self, value: str) -> str:
        cleaned = re.split(r"\b(?:for|about|regarding|role|position|interview)\b", value)[0]
        return cleaned.strip(" .,-") or "Unknown"

    def _summarize_email(self, message: EmailMessage) -> str:
        body = " ".join(message.body.split())
        return body[:600]

    def _application_status(self, category: EmailCategory) -> ApplicationStatus:
        if category in {EmailCategory.INTERVIEW_INVITATION, EmailCategory.INTERVIEW_CONFIRMATION}:
            return ApplicationStatus.INTERVIEWING
        if category == EmailCategory.OFFER:
            return ApplicationStatus.OFFER
        if category == EmailCategory.REJECTION:
            return ApplicationStatus.CLOSED
        if category == EmailCategory.APPLICATION_CONFIRMATION:
            return ApplicationStatus.APPLIED
        return ApplicationStatus.REVIEWING

    def _next_action(self, category: EmailCategory) -> str:
        actions = {
            EmailCategory.RECRUITER_OUTREACH: "Review recruiter message and draft response.",
            EmailCategory.APPLICATION_CONFIRMATION: "Wait for response; schedule follow-up.",
            EmailCategory.INTERVIEW_INVITATION: "Reply with availability and create prep brief.",
            EmailCategory.INTERVIEW_CONFIRMATION: "Prepare interview brief.",
            EmailCategory.OFFER: "Review offer and negotiation notes.",
            EmailCategory.REJECTION: "Archive opportunity and capture lessons.",
            EmailCategory.RECRUITER_FOLLOW_UP: "Reply to recruiter follow-up.",
            EmailCategory.COMPANY_COMMUNICATION: "Review message and decide next action.",
        }
        return actions.get(category, "Review message.")

    def _build_interview(
        self,
        message: EmailMessage,
        category: EmailCategory,
        company_name: str,
        role_title: str,
    ) -> InterviewRecord | None:
        interview_categories = {
            EmailCategory.INTERVIEW_INVITATION,
            EmailCategory.INTERVIEW_CONFIRMATION,
        }
        if category not in interview_categories:
            return None
        return InterviewRecord(
            title=f"{company_name} - {role_title}",
            company=company_name,
            role=role_title,
            source_thread_id=message.thread_id,
        )

    def _build_follow_up(
        self,
        message: EmailMessage,
        category: EmailCategory,
        company_name: str,
        role_title: str,
    ) -> FollowUpRecord | None:
        if category in {EmailCategory.REJECTION, EmailCategory.OFFER}:
            return None
        due_on = message.received_at.date() + timedelta(days=1)
        if category == EmailCategory.APPLICATION_CONFIRMATION:
            due_on = message.received_at.date() + timedelta(days=5)
        return FollowUpRecord(
            title=f"Follow up with {company_name} about {role_title}",
            due_on=due_on,
            draft=self._next_action(category),
        )
