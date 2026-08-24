from __future__ import annotations

from typing import TYPE_CHECKING

from tests.fixtures.mock_llm import canned_email_result, canned_opportunity_result

from career_ops.agents.gmail import GmailAgent
from career_ops.agents.opportunity import OpportunityAgent
from career_ops.agents.orchestrator import WorkflowOrchestrator
from career_ops.ai.mock import MockAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.events.log import EventLog
from career_ops.gmail.sync import GMAIL_SYNC_CHECKPOINT_KEY, GmailSyncService
from career_ops.ingestion.job_ingestion import JobIngestionPipeline
from career_ops.models import EmailMessage, EventType, NotionMutation
from career_ops.providers.jobs.base import StaticJobPageFetcher
from career_ops.providers.notion.executor import NotionGateway, NotionUpsertExecutor
from career_ops.providers.notion.mutations import NotionMutationPlanner
from career_ops.state.store import JsonStateStore

if TYPE_CHECKING:
    from career_ops.gmail.client import GmailClient

LEVER_URL = "https://jobs.lever.co/acme/mock-platform-engineer"
LEVER_HTML = """
<html>
  <head><title>Platform Engineer - Acme</title></head>
  <body>
    <h1>Platform Engineer</h1>
    <div>Acme</div>
    <p>Location: Remote - United States</p>
    <p>Compensation: $180,000 - $220,000</p>
    <p>Employment Type: Full-time</p>
    <p>Build Python distributed systems with FastAPI, Postgres, and observability.</p>
  </body>
</html>
"""


class FakeGmailClient:
    def __init__(self, message: EmailMessage, actions: list[str]) -> None:
        self.message = message
        self.actions = actions
        self.acknowledged: list[str] = []

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        assert checkpoint is None
        assert labels == ["INBOX"]
        return [self.message]

    def fetch_message(self, message_id: str) -> EmailMessage:
        assert message_id == self.message.message_id
        return self.message

    def acknowledge_processed(self, message_id: str) -> None:
        self.actions.append(f"ack:{message_id}")
        self.acknowledged.append(message_id)


class FakeNotionGateway:
    def __init__(self, actions: list[str]) -> None:
        self.actions = actions
        self.mutations: list[NotionMutation] = []

    def upsert(self, mutation: NotionMutation) -> str:
        self.actions.append(f"upsert:{mutation.dedupe_key}")
        self.mutations.append(mutation)
        return f"page:{mutation.dedupe_key}"


class FailingNotionGateway:
    def __init__(self, actions: list[str]) -> None:
        self.actions = actions

    def upsert(self, mutation: NotionMutation) -> str:
        self.actions.append(f"failed:{mutation.dedupe_key}")
        raise RuntimeError("Notion unavailable")


def test_mock_mode_runs_gmail_and_job_workflows_without_external_clients(
    tmp_path,
) -> None:
    message = EmailMessage(
        message_id="msg_mock_interview",
        thread_id="thread_mock_interview",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Platform Engineer at Acme",
        body="Please send availability so we can schedule a technical interview.",
        received_at="2026-08-24T12:00:00Z",
    )
    ai_service = MockAIService(
        email_results={message.message_id: canned_email_result()},
        opportunity_results={LEVER_URL: canned_opportunity_result()},
    )
    actions: list[str] = []
    fake_gmail = FakeGmailClient(message, actions)
    gmail_client: GmailClient = fake_gmail
    fake_notion = FakeNotionGateway(actions)
    notion_gateway: NotionGateway = fake_notion
    event_log = EventLog(tmp_path / "events.jsonl")
    notion_executor = NotionUpsertExecutor(
        gateway=notion_gateway,
        event_log=event_log,
        dry_run=False,
    )
    gmail_pipeline = GmailIngestionPipeline(ai_service=ai_service)
    gmail_sync = GmailSyncService(
        gmail_client=gmail_client,
        state_store=JsonStateStore(tmp_path / "state.json"),
        event_log=event_log,
        notion_executor=notion_executor,
        ingestion_pipeline=gmail_pipeline,
    )
    orchestrator = WorkflowOrchestrator(
        gmail_agent=GmailAgent(gmail_pipeline),
        opportunity_agent=OpportunityAgent(
            JobIngestionPipeline(
                fetcher=StaticJobPageFetcher({LEVER_URL: LEVER_HTML}),
                evaluator=ai_service,
            )
        ),
    )

    gmail_result = gmail_sync.sync(labels=["INBOX"])
    job_result = orchestrator.ingest_job_url(LEVER_URL)
    job_mutations = NotionMutationPlanner().from_job_ingestion(job_result)
    job_execution = notion_executor.execute(job_mutations)

    assert gmail_result.processed == 1
    assert gmail_result.mutations_executed == gmail_result.mutations_planned
    assert fake_gmail.acknowledged == [message.message_id]
    acknowledgement_index = actions.index(f"ack:{message.message_id}")
    gmail_mutation_actions = actions[:acknowledgement_index]
    assert len(gmail_mutation_actions) == gmail_result.mutations_planned
    assert gmail_mutation_actions == [
        f"upsert:{mutation.dedupe_key}"
        for mutation in fake_notion.mutations[: gmail_result.mutations_planned]
    ]

    assert job_result.evaluation.fit_score == 91
    assert job_result.recommended_next_action == "prioritize"
    assert job_execution.executed + job_execution.skipped == len(job_mutations)
    assert job_execution.executed == 1
    assert len(fake_notion.mutations) == gmail_result.mutations_executed + 1

    events = event_log.read_all()
    classified = next(
        event for event in events if event.event_type == EventType.GMAIL_MESSAGE_CLASSIFIED
    )
    assert classified.data["model_name"] == "mock:deterministic-v1"
    assert classified.data["fallback_status"] == "mock"
    assert any(event.event_type == EventType.NOTION_MUTATION_PLANNED for event in events)
    assert any(event.event_type == EventType.NOTION_MUTATION_APPLIED for event in events)


def test_failed_notion_execution_leaves_gmail_message_unacknowledged(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_failed_notion",
        thread_id="thread_failed_notion",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Platform Engineer at Acme",
        body="Please send availability so we can schedule a technical interview.",
        received_at="2026-08-24T12:00:00Z",
    )
    actions: list[str] = []
    fake_gmail = FakeGmailClient(message, actions)
    failing_notion = FailingNotionGateway(actions)
    event_log = EventLog(tmp_path / "events.jsonl")
    state_store = JsonStateStore(tmp_path / "state.json")
    service = GmailSyncService(
        gmail_client=fake_gmail,
        state_store=state_store,
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=failing_notion,
            event_log=event_log,
            dry_run=False,
            max_attempts=1,
        ),
        ingestion_pipeline=GmailIngestionPipeline(
            ai_service=MockAIService(
                email_results={message.message_id: canned_email_result()},
            )
        ),
    )

    result = service.sync(labels=["INBOX"])

    assert result.processed == 0
    assert result.failed == 1
    assert result.mutations_executed == 0
    assert result.errors and "Notion mutation execution failed" in result.errors[0]
    assert fake_gmail.acknowledged == []
    assert state_store.is_processed("gmail", message.message_id) is False
    assert state_store.get_checkpoint(GMAIL_SYNC_CHECKPOINT_KEY) is None
    assert any(
        event.event_type == EventType.NOTION_MUTATION_FAILED for event in event_log.read_all()
    )
