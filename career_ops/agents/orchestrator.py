from career_ops.agents.analytics import AnalyticsAgent
from career_ops.agents.gmail import GmailAgent
from career_ops.agents.opportunity import OpportunityAgent
from career_ops.models import EmailMessage, GmailIngestionPlan, JobIngestionResult


class WorkflowOrchestrator:
    """Coordinates independent agents while keeping Notion as source of truth."""

    def __init__(
        self,
        gmail_agent: GmailAgent | None = None,
        opportunity_agent: OpportunityAgent | None = None,
        analytics_agent: AnalyticsAgent | None = None,
    ) -> None:
        self.gmail_agent = gmail_agent or GmailAgent()
        self.opportunity_agent = opportunity_agent or OpportunityAgent()
        self.analytics_agent = analytics_agent or AnalyticsAgent()

    def ingest_email(self, message: EmailMessage) -> GmailIngestionPlan:
        return self.gmail_agent.plan_message(message)

    def ingest_job_url(self, url: str) -> JobIngestionResult:
        return self.opportunity_agent.ingest_url(url)
