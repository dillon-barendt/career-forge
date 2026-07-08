from collections.abc import Iterator
from contextlib import nullcontext
from typing import Protocol

from career_ops.events.log import EventLog
from career_ops.models import (
    EventType,
    NotionExecutionResult,
    NotionMutation,
    NotionMutationRecord,
    NotionMutationStatus,
)
from career_ops.observability import Observability


class NotionGateway(Protocol):
    def upsert(self, mutation: NotionMutation) -> str:
        """Upsert a mutation into Notion and return the page id."""


class NotionUpsertExecutor:
    def __init__(
        self,
        *,
        gateway: NotionGateway | None,
        event_log: EventLog,
        dry_run: bool = True,
        max_attempts: int = 3,
        observability: Observability | None = None,
    ) -> None:
        self.gateway = gateway
        self.event_log = event_log
        self.dry_run = dry_run
        self.max_attempts = max_attempts
        self.observability = observability

    def execute(self, mutations: list[NotionMutation]) -> NotionExecutionResult:
        result = NotionExecutionResult()
        executed_keys = self._executed_dedupe_keys()

        for mutation in mutations:
            with self._span(
                "career_ops.notion_mutation",
                database=mutation.database,
                dedupe_key=mutation.dedupe_key,
                dry_run=self.dry_run,
            ):
                self._append_planned(mutation)
                record = self._route_mutation(mutation, executed_keys, result)
                if record is not None:
                    result.records.append(record)

        return result

    def _route_mutation(
        self,
        mutation: NotionMutation,
        executed_keys: set[str],
        result: NotionExecutionResult,
    ) -> NotionMutationRecord | None:
        if mutation.dedupe_key in executed_keys:
            result.skipped += 1
            return NotionMutationRecord(
                mutation=mutation,
                status=NotionMutationStatus.SKIPPED_DUPLICATE,
            )

        if self.dry_run or self.gateway is None:
            result.dry_run += 1
            return NotionMutationRecord(
                mutation=mutation,
                status=NotionMutationStatus.DRY_RUN,
            )

        record = self._execute_one(mutation)
        if record.status == NotionMutationStatus.EXECUTED:
            result.executed += 1
            executed_keys.add(mutation.dedupe_key)
        else:
            result.failed += 1
        return record

    def _execute_one(self, mutation: NotionMutation) -> NotionMutationRecord:
        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                if self.gateway is None:
                    msg = "Notion gateway is required when dry_run is false."
                    raise RuntimeError(msg)
                page_id = self.gateway.upsert(mutation)
            except Exception as exc:  # noqa: BLE001 - retry boundary records external failures.
                last_error = str(exc)
                self.event_log.append(
                    event_type=EventType.ERROR_RETRY,
                    source="notion",
                    source_id=mutation.dedupe_key,
                    data={"attempt": attempt, "error": last_error},
                )
                continue

            self.event_log.append(
                event_type=EventType.NOTION_MUTATION_EXECUTED,
                source="notion",
                source_id=mutation.dedupe_key,
                data={
                    "database": mutation.database,
                    "page_id": page_id,
                    "properties": mutation.properties,
                },
            )
            return NotionMutationRecord(
                mutation=mutation,
                status=NotionMutationStatus.EXECUTED,
                page_id=page_id,
            )

        return NotionMutationRecord(
            mutation=mutation,
            status=NotionMutationStatus.FAILED,
            error=last_error,
        )

    def _append_planned(self, mutation: NotionMutation) -> None:
        self.event_log.append(
            event_type=EventType.NOTION_MUTATION_PLANNED,
            source="notion",
            source_id=mutation.dedupe_key,
            data={
                "database": mutation.database,
                "action": mutation.action,
                "properties": mutation.properties,
            },
        )

    def _executed_dedupe_keys(self) -> set[str]:
        return {
            event.source_id
            for event in self.event_log.read_all()
            if event.event_type == EventType.NOTION_MUTATION_EXECUTED
        }

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)
