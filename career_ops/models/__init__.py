from datetime import UTC, date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl

from career_ops.notion.schemas import Application, Company, Contact, JobOpportunity


class EmailCategory(StrEnum):
    RECRUITER_OUTREACH = "Recruiter Outreach"
    APPLICATION_CONFIRMATION = "Application Confirmation"
    INTERVIEW_INVITATION = "Interview Invitation"
    INTERVIEW_CONFIRMATION = "Interview Confirmation"
    OFFER = "Offer"
    REJECTION = "Rejection"
    RECRUITER_FOLLOW_UP = "Recruiter Follow-Up"
    COMPANY_COMMUNICATION = "Company Communication"
    NEWSLETTER = "Newsletter"
    IGNORE = "Ignore"


class EventType(StrEnum):
    GMAIL_MESSAGE_RECEIVED = "gmail.message.received"
    EMAIL_CLASSIFIED = "email.classified"
    COMPANY_UPSERTED = "company.upserted"
    CONTACT_UPSERTED = "contact.upserted"
    OPPORTUNITY_UPSERTED = "opportunity.upserted"
    APPLICATION_UPDATED = "application.updated"
    FOLLOW_UP_CREATED = "follow_up.created"
    INTERVIEW_DETECTED = "interview.detected"
    NOTION_MUTATION_PLANNED = "notion.mutation.planned"
    NOTION_MUTATION_EXECUTED = "notion.mutation.executed"
    AI_EVALUATION_COMPLETED = "ai.evaluation.completed"
    HUMAN_REVIEW_REQUIRED = "human_review.required"
    HUMAN_OVERRIDE_RECORDED = "human_override.recorded"
    APPLICATION_OUTCOME_RECORDED = "application.outcome.recorded"
    RECOMMENDATION_ISSUED = "recommendation.issued"
    PROMPT_EVAL_COMPLETED = "prompt_eval.completed"
    STALE_OPPORTUNITY_DETECTED = "stale_opportunity.detected"
    AGENT_FAILURE = "agent.failure"
    ERROR_RETRY = "error.retry"


class NotionMutationStatus(StrEnum):
    PLANNED = "planned"
    EXECUTED = "executed"
    DRY_RUN = "dry_run"
    SKIPPED_DUPLICATE = "skipped_duplicate"
    FAILED = "failed"


class ApplicationStage(StrEnum):
    SUBMITTED = "Submitted"
    INTERVIEWING = "Interviewing"
    OFFER = "Offer"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"


class EmailMessage(BaseModel):
    message_id: str
    thread_id: str
    sender: str
    recipients: list[str] = Field(default_factory=list)
    subject: str
    body: str
    received_at: datetime


class EmailClassification(BaseModel):
    category: EmailCategory
    confidence: float = Field(ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)
    requires_human_review: bool = False
    prompt_version: str = "email-classifier-v1"


class AuditEvent(BaseModel):
    source: str
    source_id: str
    action: str
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowEvent(BaseModel):
    event_id: str
    event_type: EventType
    source: str
    source_id: str
    data: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class InterviewRecord(BaseModel):
    title: str
    company: str
    role: str | None = None
    status: str = "Prep Needed"
    source_thread_id: str | None = None


class FollowUpRecord(BaseModel):
    title: str
    due_on: date | None = None
    channel: str = "Email"
    priority: str = "Medium"
    draft: str = ""


class GmailIngestionPlan(BaseModel):
    classification: EmailClassification
    should_mutate_notion: bool
    company: Company | None = None
    contact: Contact | None = None
    opportunity: JobOpportunity | None = None
    application: Application | None = None
    interview: InterviewRecord | None = None
    follow_up: FollowUpRecord | None = None
    audit_events: list[AuditEvent] = Field(default_factory=list)
    dedupe_key: str


class JobPosting(BaseModel):
    source_url: HttpUrl
    provider: str
    company: str
    role: str
    location: str | None = None
    compensation: str | None = None
    employment_type: str | None = None
    remote_policy: str | None = None
    description: str = ""
    skills: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    apply_url: HttpUrl | None = None


class OpportunityEvaluation(BaseModel):
    executive_summary: str
    fit_score: int = Field(ge=0, le=100)
    confidence_score: float = Field(ge=0, le=100)
    match_analysis: str
    strengths: list[str] = Field(default_factory=list)
    potential_concerns: list[str] = Field(default_factory=list)
    missing_qualifications: list[str] = Field(default_factory=list)
    resume_suggestions: list[str] = Field(default_factory=list)
    cover_letter_talking_points: list[str] = Field(default_factory=list)
    interview_preparation_topics: list[str] = Field(default_factory=list)
    suggested_next_action: str


class JobIngestionResult(BaseModel):
    provider_name: str
    posting: JobPosting
    evaluation: OpportunityEvaluation
    opportunity: JobOpportunity
    recommended_priority: str
    recommended_next_action: str
    prompt_version: str = "opportunity-evaluator-v1"
    needs_human_review: bool = False


class AnalyticsApplication(BaseModel):
    company: str
    source: str
    stage: ApplicationStage
    submitted_on: date
    first_response_on: date | None = None


class AnalyticsContact(BaseModel):
    name: str
    contacted_on: date
    responded: bool = False


class WeeklyAnalyticsInput(BaseModel):
    week_start: date
    applications: list[AnalyticsApplication] = Field(default_factory=list)
    contacts: list[AnalyticsContact] = Field(default_factory=list)


class WeeklyAnalytics(BaseModel):
    applications_submitted: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    pipeline_conversion: dict[str, int] = Field(default_factory=dict)
    average_time_to_response_days: float | None = None
    recruiter_response_rate: float
    source_effectiveness: dict[str, int] = Field(default_factory=dict)
    company_activity: dict[str, int] = Field(default_factory=dict)
    weekly_recommendations: list[str] = Field(default_factory=list)


class NotionMutation(BaseModel):
    database: str
    dedupe_key: str
    action: str
    properties: dict[str, object]


class NotionMutationRecord(BaseModel):
    mutation: NotionMutation
    status: NotionMutationStatus
    page_id: str | None = None
    error: str | None = None


class NotionExecutionResult(BaseModel):
    executed: int = 0
    dry_run: int = 0
    skipped: int = 0
    failed: int = 0
    records: list[NotionMutationRecord] = Field(default_factory=list)


class PydanticAIEmailEvaluation(BaseModel):
    classification: EmailCategory
    confidence_score: float = Field(ge=0, le=1)
    executive_summary: str
    suggested_next_action: str
    human_review_required: bool
    reasons: list[str] = Field(default_factory=list)
    prompt_version: str = "email-classifier-v1"


class GmailSyncResult(BaseModel):
    fetched: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    mutations_planned: int = 0
    mutations_executed: int = 0
    human_review_required: int = 0
    errors: list[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    agent_name: str
    success: bool
    summary: str
    audit_events: list[AuditEvent] = Field(default_factory=list)


__all__ = [
    "AgentResult",
    "AnalyticsApplication",
    "AnalyticsContact",
    "ApplicationStage",
    "AuditEvent",
    "EmailCategory",
    "EmailClassification",
    "EmailMessage",
    "EventType",
    "FollowUpRecord",
    "GmailIngestionPlan",
    "GmailSyncResult",
    "InterviewRecord",
    "JobIngestionResult",
    "JobPosting",
    "NotionExecutionResult",
    "NotionMutation",
    "NotionMutationRecord",
    "NotionMutationStatus",
    "OpportunityEvaluation",
    "PydanticAIEmailEvaluation",
    "WeeklyAnalytics",
    "WeeklyAnalyticsInput",
    "WorkflowEvent",
]
