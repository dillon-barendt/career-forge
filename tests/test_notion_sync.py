from career_ops.events.log import EventLog
from career_ops.models import EventType, NotionMutation, NotionMutationStatus
from career_ops.providers.notion.executor import NotionUpsertExecutor


class FakeNotionGateway:
    def __init__(self) -> None:
        self.upserts: list[NotionMutation] = []

    def upsert(self, mutation: NotionMutation) -> str:
        self.upserts.append(mutation)
        return f"page_{len(self.upserts)}"


def test_notion_executor_dry_run_records_planned_without_writing(tmp_path) -> None:
    gateway = FakeNotionGateway()
    executor = NotionUpsertExecutor(
        gateway=gateway,
        event_log=EventLog(tmp_path / "events.jsonl"),
        dry_run=True,
    )

    result = executor.execute(
        [
            NotionMutation(
                database="companies",
                dedupe_key="company:acme",
                action="upsert",
                properties={"Name": "Acme"},
            )
        ]
    )

    assert result.executed == 0
    assert result.dry_run == 1
    assert gateway.upserts == []
    assert result.records[0].status == NotionMutationStatus.DRY_RUN


def test_notion_executor_skips_duplicate_dedupe_keys(tmp_path) -> None:
    gateway = FakeNotionGateway()
    log = EventLog(tmp_path / "events.jsonl")
    executor = NotionUpsertExecutor(gateway=gateway, event_log=log, dry_run=False)
    mutation = NotionMutation(
        database="companies",
        dedupe_key="company:acme",
        action="upsert",
        properties={"Name": "Acme"},
    )

    first = executor.execute([mutation])
    second = executor.execute([mutation])

    assert first.executed == 1
    assert second.skipped == 1
    assert len(gateway.upserts) == 1
    assert any(event.event_type == EventType.NOTION_MUTATION_EXECUTED for event in log.read_all())
