import pytest

from career_ops.events.log import EventLog
from career_ops.models import (
    EventStatus,
    EventType,
    NotionMutation,
    NotionMutationStatus,
)
from career_ops.operator_loop import NotionReplayError, NotionReplayService
from career_ops.providers.notion.executor import NotionSchemaValidationResult, NotionUpsertExecutor


class FakeNotionGateway:
    def __init__(self) -> None:
        self.upserts: list[NotionMutation] = []

    def validate_database_schema(self, database: str) -> NotionSchemaValidationResult:
        return NotionSchemaValidationResult.valid(database=database)

    def upsert(self, mutation: NotionMutation) -> str:
        self.upserts.append(mutation)
        return f"page:{mutation.dedupe_key}"


class FailingNotionGateway:
    def validate_database_schema(self, database: str) -> NotionSchemaValidationResult:
        return NotionSchemaValidationResult.valid(database=database)

    def upsert(self, mutation: NotionMutation) -> str:
        raise RuntimeError("notion unavailable")


def _mutation(*, requires_review: bool = False) -> NotionMutation:
    return NotionMutation(
        database="companies",
        dedupe_key="company:acme",
        action="upsert",
        properties={"Name": "Acme"},
        requires_review=requires_review,
        source_message_id="msg_1",
    )


def _append_plan(log: EventLog, mutation: NotionMutation):
    return log.append(
        event_type=EventType.NOTION_MUTATION_PLANNED,
        source="notion",
        source_id=mutation.dedupe_key,
        data={"mutation": mutation.model_dump(mode="json")},
        status=EventStatus.PLANNED,
        replay_eligible=not mutation.requires_review,
    )


def test_notion_replay_inspects_latest_plan(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    planned = _append_plan(log, _mutation())
    service = NotionReplayService(
        event_log=log,
        notion_executor=NotionUpsertExecutor(gateway=None, event_log=log, dry_run=True),
    )

    result = service.inspect_latest_plan()

    assert result.event.event_id == planned.event_id
    assert result.mutation.dedupe_key == "company:acme"
    assert result.replay_eligible is True


def test_notion_replay_applies_latest_plan_in_dry_run(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    _append_plan(log, _mutation())
    service = NotionReplayService(
        event_log=log,
        notion_executor=NotionUpsertExecutor(gateway=None, event_log=log, dry_run=True),
    )

    result = service.apply_latest(dry_run=True)

    assert result.execution.dry_run == 1
    assert result.execution.executed == 0
    assert result.mutation.dedupe_key == "company:acme"


def test_notion_replay_refuses_low_confidence_plan_without_confirmation(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    _append_plan(log, _mutation(requires_review=True))
    service = NotionReplayService(
        event_log=log,
        notion_executor=NotionUpsertExecutor(
            gateway=FakeNotionGateway(),
            event_log=log,
            dry_run=False,
        ),
    )

    with pytest.raises(NotionReplayError, match="requires review"):
        service.apply_latest(dry_run=False, confirm=False)


def test_notion_replay_previews_low_confidence_plan_in_dry_run(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    _append_plan(log, _mutation(requires_review=True))
    service = NotionReplayService(
        event_log=log,
        notion_executor=NotionUpsertExecutor(gateway=None, event_log=log, dry_run=True),
    )

    result = service.apply_latest(dry_run=True, confirm=False)

    assert result.execution.dry_run == 1
    assert result.mutation.requires_review is True


def test_notion_replay_records_gateway_failure_for_replay(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    _append_plan(log, _mutation())
    service = NotionReplayService(
        event_log=log,
        notion_executor=NotionUpsertExecutor(
            gateway=FailingNotionGateway(),
            event_log=log,
            dry_run=False,
            max_attempts=1,
        ),
    )

    result = service.apply_latest(dry_run=False, confirm=True)

    assert result.execution.failed == 1
    assert result.execution.records[0].status == NotionMutationStatus.FAILED
    events = log.read_all()
    assert any(event.event_type == EventType.NOTION_MUTATION_FAILED for event in events)
    assert any(
        event.replay_eligible
        for event in events
        if event.event_type == EventType.NOTION_MUTATION_FAILED
    )
