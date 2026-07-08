from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.models import EmailMessage, GmailIngestionPlan


class GmailAgent:
    name = "Gmail Agent"

    def __init__(self, pipeline: GmailIngestionPipeline | None = None) -> None:
        self.pipeline = pipeline or GmailIngestionPipeline()

    def plan_message(self, message: EmailMessage) -> GmailIngestionPlan:
        return self.pipeline.plan(message)
