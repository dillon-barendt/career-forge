import json
from pathlib import Path
from uuid import uuid4

from career_ops.models import EventStatus, EventType, WorkflowEvent


class EventLog:
    """Append-only JSONL event log for replay and debugging."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        *,
        event_type: EventType,
        source: str,
        source_id: str,
        data: dict[str, object] | None = None,
        correlation_id: str | None = None,
        actor: str = "system",
        status: EventStatus = EventStatus.COMPLETED,
        error_details: str | None = None,
        replay_eligible: bool = False,
        redacted_payload_summary: dict[str, object] | None = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            source=source,
            source_id=source_id,
            data=data or {},
            correlation_id=correlation_id,
            actor=actor,
            status=status,
            error_details=error_details,
            replay_eligible=replay_eligible,
            redacted_payload_summary=redacted_payload_summary or {},
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(event.model_dump_json())
            handle.write("\n")
        return event

    def read_all(self) -> list[WorkflowEvent]:
        if not self.path.exists():
            return []
        events: list[WorkflowEvent] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    events.append(WorkflowEvent.model_validate(json.loads(line)))
        return events

    def tail(self, limit: int) -> list[WorkflowEvent]:
        if limit <= 0:
            return []
        return self.read_all()[-limit:]

    def get(self, event_id: str) -> WorkflowEvent | None:
        for event in self.read_all():
            if event.event_id == event_id:
                return event
        return None

    def latest(self, event_type: EventType) -> WorkflowEvent | None:
        for event in reversed(self.read_all()):
            if event.event_type == event_type:
                return event
        return None
