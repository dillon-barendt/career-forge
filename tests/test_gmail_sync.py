from career_ops.ai.deterministic import DeterministicAIService
from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.events.log import EventLog
from career_ops.gmail.sync import GmailSyncService
from career_ops.models import (
    EmailMessage,
    EventType,
    GmailIngestionPlan,
    NotionMutation,
    PydanticAIEmailEvaluation,
)
from career_ops.providers.notion.executor import NotionUpsertExecutor
from career_ops.providers.notion.mutations import NotionMutationPlanner


class FakeGmailClient:
    def __init__(self, messages: list[EmailMessage]) -> None:
        self.messages = messages
        self.acknowledged: list[str] = []

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        assert labels == ["INBOX"]
        return self.messages

    def acknowledge_processed(self, message_id: str) -> None:
        self.acknowledged.append(message_id)


class CheckpointAwareGmailClient(FakeGmailClient):
    """Models the chronological frontier returned by the real Gmail client."""

    def __init__(self, messages: list[EmailMessage]) -> None:
        super().__init__(messages)
        self.requested_checkpoints: list[str | None] = []

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        assert labels == ["INBOX"]
        self.requested_checkpoints.append(checkpoint)
        if checkpoint is None:
            return self.messages
        message_ids = [message.message_id for message in self.messages]
        if checkpoint not in message_ids:
            return self.messages
        return self.messages[message_ids.index(checkpoint) + 1 :]


class RetryableBatchAcknowledgementGmailClient(CheckpointAwareGmailClient):
    def __init__(self, messages: list[EmailMessage]) -> None:
        super().__init__(messages)
        self.acknowledgement_attempts = 0

    def acknowledge_processed(self, message_id: str) -> None:
        self.acknowledgement_attempts += 1
        if self.acknowledgement_attempts == 1:
            raise RuntimeError("temporary Gmail acknowledgement failure")
        super().acknowledge_processed(message_id)


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


class FailingMutationPlanner(NotionMutationPlanner):
    def from_gmail_plan(self, plan: GmailIngestionPlan) -> list[NotionMutation]:
        raise RuntimeError("mutation planning failed")


class FailingPlanningPipeline(GmailIngestionPipeline):
    def plan(self, message: EmailMessage) -> GmailIngestionPlan:
        raise RuntimeError("message planning failed")


class FailingEmailClassificationService:
    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        raise RuntimeError("classification provider failed")


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

    def finalize_processed(
        self,
        source: str,
        source_id: str,
        *,
        checkpoint_key: str,
        checkpoint_value: str,
    ) -> None:
        self.processed.add(source_id)
        self.checkpoint = checkpoint_value


class RetryableFinalizationStateStore(FakeStateStore):
    def __init__(self) -> None:
        super().__init__()
        self.finalization_attempts = 0

    def set_checkpoint(self, key: str, value: str) -> None:
        raise RuntimeError("legacy split checkpoint persistence failure")

    def finalize_processed(
        self,
        source: str,
        source_id: str,
        *,
        checkpoint_key: str,
        checkpoint_value: str,
    ) -> None:
        self.finalization_attempts += 1
        if self.finalization_attempts == 1:
            raise RuntimeError("temporary local finalization failure")
        super().finalize_processed(
            source,
            source_id,
            checkpoint_key=checkpoint_key,
            checkpoint_value=checkpoint_value,
        )


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


def test_gmail_sync_reports_mutation_planning_failure_as_processing_failure(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_processing_failure",
        thread_id="thread_processing_failure",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    client = FakeGmailClient([message])
    event_log = EventLog(tmp_path / "events.jsonl")
    service = GmailSyncService(
        gmail_client=client,
        state_store=FakeStateStore(),
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=FakeNotionGateway(),
            event_log=event_log,
            dry_run=False,
        ),
        mutation_planner=FailingMutationPlanner(),
    )

    result = service.sync(labels=["INBOX"])

    assert result.processed == 0
    assert result.failed == 1
    assert client.acknowledged == []
    message_events = [
        event for event in event_log.read_all() if event.source_id == message.message_id
    ]
    event_types = [event.event_type.value for event in message_events]
    assert "gmail.message.processing_failed" in event_types
    assert "gmail.message.classification_failed" not in event_types
    retry_event = next(
        event for event in message_events if event.event_type == EventType.ERROR_RETRY
    )
    assert retry_event.data["stage"] == "mutation_planning"


def test_gmail_sync_reports_non_classification_plan_failure_as_processing_failure(
    tmp_path,
) -> None:
    message = EmailMessage(
        message_id="msg_plan_failure",
        thread_id="thread_plan_failure",
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
        ingestion_pipeline=FailingPlanningPipeline(
            ai_service=DeterministicAIService(),
        ),
    )

    result = service.sync(labels=["INBOX"])

    assert result.failed == 1
    message_events = [
        event for event in event_log.read_all() if event.source_id == message.message_id
    ]
    event_types = [event.event_type.value for event in message_events]
    assert "gmail.message.processing_failed" in event_types
    assert "gmail.message.classification_failed" not in event_types
    retry_event = next(
        event for event in message_events if event.event_type == EventType.ERROR_RETRY
    )
    assert retry_event.data["stage"] == "message_planning"


def test_gmail_sync_keeps_ai_classification_failure_taxonomy(tmp_path) -> None:
    message = EmailMessage(
        message_id="msg_classification_failure",
        thread_id="thread_classification_failure",
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
            ai_service=FailingEmailClassificationService(),
        ),
    )

    result = service.sync(labels=["INBOX"])

    assert result.failed == 1
    message_events = [
        event for event in event_log.read_all() if event.source_id == message.message_id
    ]
    event_types = [event.event_type.value for event in message_events]
    assert "gmail.message.classification_failed" in event_types
    assert "gmail.message.processing_failed" not in event_types
    retry_event = next(
        event for event in message_events if event.event_type == EventType.ERROR_RETRY
    )
    assert retry_event.data["stage"] == "classification"


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
    first_events = [
        event for event in event_log.read_all() if event.source_id == message.message_id
    ]
    first_event_types = [event.event_type.value for event in first_events]
    assert "gmail.message.acknowledgement_failed" in first_event_types
    assert "gmail.message.classification_failed" not in first_event_types
    assert first_event_types.count("gmail.message.classified") == 1
    retry_event = next(event for event in first_events if event.event_type == EventType.ERROR_RETRY)
    assert retry_event.data["stage"] == "acknowledgement"

    second = service.sync(labels=["INBOX"])

    assert second.processed == 1
    assert second.failed == 0
    assert client.acknowledged == [message.message_id]
    assert state.processed == {message.message_id}
    assert state.checkpoint == message.message_id
    all_event_types = [
        event.event_type.value
        for event in event_log.read_all()
        if event.source_id == message.message_id
    ]
    assert all_event_types.count("gmail.message.acknowledgement_failed") == 1
    assert all_event_types.count("gmail.message.classification_failed") == 0
    assert all_event_types.count("gmail.message.classified") == 2


def test_gmail_sync_stops_at_failed_checkpoint_frontier_then_retries_in_order(
    tmp_path,
) -> None:
    older = EmailMessage(
        message_id="msg_older",
        thread_id="thread_older",
        sender="Older Recruiter <older@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    newer = EmailMessage(
        message_id="msg_newer",
        thread_id="thread_newer",
        sender="Newer Recruiter <newer@example.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Platform Engineer at Example",
        body="We would like to schedule another technical interview.",
        received_at="2026-07-08T16:00:00Z",
    )
    state = FakeStateStore()
    client = RetryableBatchAcknowledgementGmailClient([older, newer])
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

    assert first.fetched == 2
    assert first.processed == 0
    assert first.failed == 1
    assert state.processed == set()
    assert state.checkpoint is None
    first_event_source_ids = [event.source_id for event in event_log.read_all()]
    assert older.message_id in first_event_source_ids
    assert newer.message_id not in first_event_source_ids

    second = service.sync(labels=["INBOX"])

    assert second.fetched == 2
    assert second.processed == 2
    assert second.failed == 0
    assert client.requested_checkpoints == [None, None]
    assert client.acknowledged == [older.message_id, newer.message_id]
    assert state.processed == {older.message_id, newer.message_id}
    assert state.checkpoint == newer.message_id
    classified_source_ids = [
        event.source_id
        for event in event_log.read_all()
        if event.event_type == EventType.GMAIL_MESSAGE_CLASSIFIED
    ]
    assert classified_source_ids == [older.message_id, older.message_id, newer.message_id]


def test_gmail_sync_recovers_local_finalization_separately_from_classification(
    tmp_path,
) -> None:
    message = EmailMessage(
        message_id="msg_finalize_retry",
        thread_id="thread_finalize_retry",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body="We would like to schedule a technical interview.",
        received_at="2026-07-07T16:00:00Z",
    )
    state = RetryableFinalizationStateStore()
    client = FakeGmailClient([message])
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
    assert client.acknowledged == [message.message_id]
    assert state.processed == set()
    assert state.checkpoint is None
    first_events = [
        event for event in event_log.read_all() if event.source_id == message.message_id
    ]
    first_event_types = [event.event_type.value for event in first_events]
    assert "gmail.message.finalization_failed" in first_event_types
    assert "gmail.message.classification_failed" not in first_event_types
    retry_event = next(event for event in first_events if event.event_type == EventType.ERROR_RETRY)
    assert retry_event.data["stage"] == "local_finalization"

    second = service.sync(labels=["INBOX"])

    assert second.processed == 1
    assert second.failed == 0
    assert client.acknowledged == [message.message_id, message.message_id]
    assert state.processed == {message.message_id}
    assert state.checkpoint == message.message_id
