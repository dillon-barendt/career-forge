from datetime import datetime

from pydantic import BaseModel, ConfigDict

from career_ops.agents.gmail import GmailAgent
from career_ops.agents.opportunity import OpportunityAgent
from career_ops.agents.orchestrator import WorkflowOrchestrator
from career_ops.ai.contracts import CareerAIService
from career_ops.ai.mock import MockAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.compat import UTC
from career_ops.ingestion.job_ingestion import JobIngestionPipeline
from career_ops.materials.resume_tailor import build_resume_tailoring_notes
from career_ops.models import EmailMessage
from career_ops.providers.jobs.base import StaticJobPageFetcher

DEMO_JOB_URL = "https://jobs.lever.co/acme/principal-platform-engineer"
DEMO_JOB_HTML = """
<html>
  <head><title>Principal Platform Engineer - Acme</title></head>
  <body>
    <h1>Principal Platform Engineer</h1>
    <div>Acme</div>
    <p>Location: Remote - United States</p>
    <p>Compensation: $190,000 - $230,000</p>
    <p>Employment Type: Full-time</p>
    <p>
      Build Python and FastAPI services for distributed systems, agentic automation,
      Postgres data products, and observable integration workflows.
    </p>
  </body>
</html>
"""

ShowcaseValue = str | int | float | bool


class ShowcaseScenario(BaseModel):
    """Captures one prompt and its typed, reviewer-facing outcome."""

    model_config = ConfigDict(frozen=True)

    slug: str
    title: str
    prompt: str
    result: dict[str, ShowcaseValue]


class ShowcaseReport(BaseModel):
    """Groups the stable outputs produced by the credential-free demo."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    mode: str = "mock"
    scenarios: list[ShowcaseScenario]


class ShowcaseRunner:
    """Runs representative career workflows through the real agent boundaries."""

    def __init__(self, ai_service: CareerAIService | None = None) -> None:
        service = ai_service if ai_service is not None else MockAIService()
        self.orchestrator = WorkflowOrchestrator(
            gmail_agent=GmailAgent(GmailIngestionPipeline(ai_service=service)),
            opportunity_agent=OpportunityAgent(
                JobIngestionPipeline(
                    fetcher=StaticJobPageFetcher({DEMO_JOB_URL: DEMO_JOB_HTML}),
                    evaluator=service,
                )
            ),
        )

    def run(self) -> ShowcaseReport:
        email_plan = self.orchestrator.ingest_email(self._interview_email())
        job_result = self.orchestrator.ingest_job_url(DEMO_JOB_URL)
        resume = build_resume_tailoring_notes(job_result.opportunity)

        return ShowcaseReport(
            scenarios=[
                ShowcaseScenario(
                    slug="triage-interview-email",
                    title="Triage an interview invitation",
                    prompt=(
                        "Classify this recruiter email and propose the next safe workflow action."
                    ),
                    result={
                        "classification": email_plan.classification.category.value,
                        "confidence": email_plan.classification.confidence,
                        "next_action": (
                            email_plan.application.next_action or "Review message."
                            if email_plan.application
                            else "Review message."
                        ),
                        "notion_write": "planned" if email_plan.should_mutate_notion else "skipped",
                    },
                ),
                ShowcaseScenario(
                    slug="evaluate-platform-role",
                    title="Evaluate a platform role",
                    prompt=(
                        "Extract this job posting, score fit, and recommend "
                        "whether to prioritize it."
                    ),
                    result={
                        "provider": job_result.provider_name,
                        "role": job_result.posting.role,
                        "fit_score": job_result.evaluation.fit_score,
                        "priority": job_result.recommended_priority,
                        "next_action": job_result.recommended_next_action,
                    },
                ),
                ShowcaseScenario(
                    slug="tailor-resume",
                    title="Tailor the resume",
                    prompt=(
                        "Create truthful resume-tailoring notes from the evaluated opportunity."
                    ),
                    result={
                        "kind": resume.kind,
                        "company": resume.company or "Unknown",
                        "preview": resume.body.splitlines()[0],
                    },
                ),
            ]
        )

    @staticmethod
    def _interview_email() -> EmailMessage:
        return EmailMessage(
            message_id="demo-interview-001",
            thread_id="demo-thread-001",
            sender="Avery Recruiter <avery@acme.com>",
            recipients=["candidate@example.com"],
            subject="Interview invitation for Principal Platform Engineer at Acme",
            body=(
                "We would like to schedule a technical interview. "
                "Please send your availability for next week."
            ),
            received_at=datetime(2026, 8, 24, 12, tzinfo=UTC),
        )
