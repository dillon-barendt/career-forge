from career_ops.events.log import EventLog
from career_ops.models import EventType, NotionMutation, NotionMutationStatus
from career_ops.providers.notion.executor import NotionSchemaValidationResult, NotionUpsertExecutor


class MissingDedupeSchemaGateway:
    def __init__(self) -> None:
        self.upsert_called = False

    def validate_database_schema(self, database: str) -> NotionSchemaValidationResult:
        return NotionSchemaValidationResult(
            database=database,
            ok=False,
            errors=["Database is missing required rich_text property: Dedupe Key"],
            warnings=[],
        )

    def upsert(self, mutation: NotionMutation) -> str:
        self.upsert_called = True
        return "unexpected"


def test_notion_executor_validates_dedupe_key_schema_before_live_write(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")
    gateway = MissingDedupeSchemaGateway()
    executor = NotionUpsertExecutor(gateway=gateway, event_log=log, dry_run=False)
    mutation = NotionMutation(
        database="companies",
        dedupe_key="company:acme",
        action="upsert",
        properties={"Name": "Acme"},
    )

    result = executor.execute([mutation])

    assert result.failed == 1
    assert result.records[0].status == NotionMutationStatus.FAILED
    assert "Dedupe Key" in (result.records[0].error or "")
    assert gateway.upsert_called is False
    assert any(event.event_type == EventType.NOTION_MUTATION_FAILED for event in log.read_all())
