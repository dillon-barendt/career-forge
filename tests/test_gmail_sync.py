from career_ops.ai.deterministic import DeterministicAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.events.log import EventLog
from career_ops.gmail.sync import GmailSyncService
from career_ops.models import EmailMessage, EventType
from career_ops.providers.notion.executor import NotionUpsertExecutor


class FakeGmailClient:
    def __init__(self, messages: list[EmailMessage]) -> None:
        self.messages = messages
        self.acknowledged: list[str] = []

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        assert labels == ["INBOX"]
        return self.messages

    def acknowledge_processed(self, message_id: str) -> None:
        self.acknowledged.append(message_id)


class RetryableAcknowledgementGmailClient(FakeGmailClient):
    def __init__(self, messages: list[EmailMessage]) -> None:
        super().__init__(messages)
        self.acknowledgement_attempts = 0

    def acknowledge_processed(self, message_id: str) -> None:
        self.acknowledgement_attempts += 1
        if self.acknowledgement_attempts == 1:
            raise RuntimeError("temporary Gmail acknowledgement failure")
        super().acknowledge_processed(message_id)


class FakeNotionGateway:
    def upsert(self, mutation) -> str:
        return f"page:{mutation.dedupe_key}"


class FakeStateStore:
    def __init__(self) -> None:
        self.processed: set[str] = set()
        self.checkpoint: str | None = None

    def get_checkpoint(self, key: str) -> str | None:
        return self.checkpoint

    def set_checkpoint(self, key: str, value: str) -> None:
        self.checkpoint = value

    def is_processed(self, source: str, source_id: str) -> bool:
        return source_id in self.processed

    def mark_processed(self, source: str, source_id: str) -> None:
        self.processed.add(source_id)


def test_gmail_sync_processes_new_messages_and_skips_processed(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    state = FakeStateStore()
    client = FakeGmailClient([message])
    event_log = EventLog(tmp_path / "events.jsonl")
    notion_executor = NotionUpsertExecutor(
        gateway=FakeNotionGateway(),
        event_log=event_log,
        dry_run=False,
    )
    service = GmailSyncService(
        gmail_client=client,
        state_store=state,
        event_log=event_log,
        notion_executor=notion_executor,
    )

    first = service.sync(labels=["INBOX"])
    second = service.sync(labels=["INBOX"])

    assert first.processed == 1
    assert first.mutations_planned > 0
    assert second.skipped == 1
    assert client.acknowledged == ["msg_1"]
    assert state.checkpoint == "msg_1"


def test_gmail_sync_dry_run_does_not_acknowledge_or_checkpoint(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    state = FakeStateStore()
    client = FakeGmailClient([message])
    event_log = EventLog(tmp_path / "events.jsonl")
    notion_executor = NotionUpsertExecutor(gateway=None, event_log=event_log, dry_run=True)
    service = GmailSyncService(
        gmail_client=client,
        state_store=state,
        event_log=event_log,
        notion_executor=notion_executor,
    )

    result = service.sync(labels=["INBOX"])

    assert result.processed == 1
    assert client.acknowledged == []
    assert state.checkpoint is None
    assert state.processed == set()


def test_gmail_sync_uses_classification_metadata_without_provider_internals(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_metadata",
        thread_id="thread_metadata",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    event_log = EventLog(tmp_path / "events.jsonl")
    service = GmailSyncService(
        gmail_client=FakeGmailClient([message]),
        state_store=FakeStateStore(),
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=FakeNotionGateway(),
            event_log=event_log,
            dry_run=False,
        ),
        ingestion_pipeline=GmailIngestionPipeline(
            ai_service=DeterministicAIService(),
        ),
    )

    result = service.sync(labels=["INBOX"])

    assert result.processed == 1
    classified = next(
        event
        for event in event_log.read_all()
        if event.event_type == EventType.GMAIL_MESSAGE_CLASSIFIED
    )
    assert classified.data["model_name"] == "deterministic:rules-v1"
    assert classified.data["fallback_status"] == "deterministic"


def test_gmail_sync_retries_when_provider_acknowledgement_fails(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_ack_retry",
        thread_id="thread_ack_retry",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    state = FakeStateStore()
    client = RetryableAcknowledgementGmailClient([message])
    event_log = EventLog(tmp_path / "events.jsonl")
    service = GmailSyncService(
        gmail_client=client,
        state_store=state,
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=FakeNotionGateway(),
            event_log=event_log,
            dry_run=False,
        ),
    )

    first = service.sync(labels=["INBOX"])

    assert first.processed == 0
    assert first.failed == 1
    assert state.processed == set()
    assert state.checkpoint is None

    second = service.sync(labels=["INBOX"])

    assert second.processed == 1
    assert second.failed == 0
    assert client.acknowledged == [message.message_id]
    assert state.processed == {message.message_id}
    assert state.checkpoint == message.message_id
