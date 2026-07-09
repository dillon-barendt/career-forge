from pydantic import BaseModel

from career_ops.events.log import EventLog
from career_ops.models import (
    EventStatus,
    EventType,
    NotionExecutionResult,
    NotionMutation,
    WorkflowEvent,
)
from career_ops.providers.notion.executor import NotionUpsertExecutor


class NotionReplayError(RuntimeError):
    """Raised when a planned mutation cannot be replayed safely."""


class NotionPlanInspection(BaseModel):
    event: WorkflowEvent
    mutation: NotionMutation
    replay_eligible: bool


class NotionApplyResult(BaseModel):
    event: WorkflowEvent
    mutation: NotionMutation
    execution: NotionExecutionResult


class NotionReplayService:
    """Inspect and replay append-only Notion mutation plans."""

    def __init__(self, *, event_log: EventLog, notion_executor: NotionUpsertExecutor) -> None:
        self.event_log = event_log
        self.notion_executor = notion_executor

    def inspect_latest_plan(self) -> NotionPlanInspection:
        event = self._latest_planned_event()
        return self._inspect_event(event)

    def inspect_event(self, event_id: str) -> NotionPlanInspection:
        event = self.event_log.get(event_id)
        if event is None:
            msg = f"No event found for id {event_id!r}."
            raise NotionReplayError(msg)
        if event.event_type != EventType.NOTION_MUTATION_PLANNED:
            msg = f"Event {event_id!r} is not a Notion mutation plan."
            raise NotionReplayError(msg)
        return self._inspect_event(event)

    def apply_latest(self, *, dry_run: bool, confirm: bool = False) -> NotionApplyResult:
        event = self._latest_unapplied_plan()
        return self._apply_event(event, dry_run=dry_run, confirm=confirm)

    def apply_event(
        self,
        event_id: str,
        *,
        dry_run: bool,
        confirm: bool = False,
    ) -> NotionApplyResult:
        inspection = self.inspect_event(event_id)
        return self._apply_inspection(inspection, dry_run=dry_run, confirm=confirm)

    def _inspect_event(self, event: WorkflowEvent) -> NotionPlanInspection:
        mutation = self._mutation_from_event(event)
        return NotionPlanInspection(
            event=event,
            mutation=mutation,
            replay_eligible=event.replay_eligible and not mutation.requires_review,
        )

    def _apply_event(
        self,
        event: WorkflowEvent,
        *,
        dry_run: bool,
        confirm: bool,
    ) -> NotionApplyResult:
        inspection = self._inspect_event(event)
        return self._apply_inspection(inspection, dry_run=dry_run, confirm=confirm)

    def _apply_inspection(
        self,
        inspection: NotionPlanInspection,
        *,
        dry_run: bool,
        confirm: bool,
    ) -> NotionApplyResult:
        mutation = inspection.mutation
        if mutation.requires_review and not dry_run and not confirm:
            self.event_log.append(
                event_type=EventType.OPERATOR_REVIEW_REQUIRED,
                source="notion",
                source_id=mutation.dedupe_key,
                data={
                    "reason": "planned mutation requires review",
                    "plan_event_id": inspection.event.event_id,
                },
                status=EventStatus.REVIEW_REQUIRED,
            )
            msg = "Planned mutation requires review before apply."
            raise NotionReplayError(msg)
        if not dry_run and not confirm:
            msg = "Live Notion apply requires --confirm."
            raise NotionReplayError(msg)
        if dry_run != self.notion_executor.dry_run:
            msg = "Replay executor dry-run mode does not match the requested apply mode."
            raise NotionReplayError(msg)
        if self._is_applied(mutation.dedupe_key):
            self.event_log.append(
                event_type=EventType.NOTION_MUTATION_SKIPPED,
                source="notion",
                source_id=mutation.dedupe_key,
                data={"reason": "already_applied", "plan_event_id": inspection.event.event_id},
                status=EventStatus.SKIPPED,
            )
            msg = f"Mutation {mutation.dedupe_key!r} was already applied."
            raise NotionReplayError(msg)
        execution = self.notion_executor.execute([mutation])
        if self.notion_executor.observability is not None:
            self.notion_executor.observability.increment(
                "career_forge.operator.replay",
                status="dry_run" if dry_run else "apply",
            )
        return NotionApplyResult(
            event=inspection.event,
            mutation=mutation,
            execution=execution,
        )

    def _latest_planned_event(self) -> WorkflowEvent:
        for event in reversed(self.event_log.read_all()):
            if event.event_type == EventType.NOTION_MUTATION_PLANNED:
                return event
        msg = "No Notion mutation plan events were found."
        raise NotionReplayError(msg)

    def _latest_unapplied_plan(self) -> WorkflowEvent:
        applied = self._applied_dedupe_keys()
        for event in reversed(self.event_log.read_all()):
            if event.event_type != EventType.NOTION_MUTATION_PLANNED:
                continue
            mutation = self._mutation_from_event(event)
            if mutation.dedupe_key not in applied:
                return event
        msg = "No unapplied Notion mutation plan events were found."
        raise NotionReplayError(msg)

    def _mutation_from_event(self, event: WorkflowEvent) -> NotionMutation:
        raw = event.data.get("mutation")
        if isinstance(raw, dict):
            return NotionMutation.model_validate(raw)
        return NotionMutation(
            database=str(event.data.get("database", "")),
            dedupe_key=event.source_id,
            action=str(event.data.get("action", "upsert")),
            properties=dict(event.data.get("properties", {})),
            requires_review=bool(event.data.get("requires_review", False)),
        )

    def _is_applied(self, dedupe_key: str) -> bool:
        return dedupe_key in self._applied_dedupe_keys()

    def _applied_dedupe_keys(self) -> set[str]:
        return {
            event.source_id
            for event in self.event_log.read_all()
            if event.event_type
            in {EventType.NOTION_MUTATION_APPLIED, EventType.NOTION_MUTATION_EXECUTED}
        }
