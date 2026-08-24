from collections.abc import Iterator
from contextlib import nullcontext

from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.events.log import EventLog
from career_ops.gmail.client import GmailClient
from career_ops.models import EmailMessage, EventStatus, EventType, GmailSyncResult
from career_ops.observability import Observability
from career_ops.providers.notion.executor import NotionUpsertExecutor
from career_ops.providers.notion.mutations import NotionMutationPlanner
from career_ops.state.store import StateStore

GMAIL_SYNC_CHECKPOINT_KEY = "gmail:last_message_id"


class GmailSyncService:
    def __init__(
        self,
        *,
        gmail_client: GmailClient,
        state_store: StateStore,
        event_log: EventLog,
        notion_executor: NotionUpsertExecutor,
        ingestion_pipeline: GmailIngestionPipeline | None = None,
        mutation_planner: NotionMutationPlanner | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.gmail_client = gmail_client
        self.state_store = state_store
        self.event_log = event_log
        self.notion_executor = notion_executor
        self.ingestion_pipeline = ingestion_pipeline or GmailIngestionPipeline()
        self.mutation_planner = mutation_planner or NotionMutationPlanner()
        self.observability = observability

    def sync(self, labels: list[str] | None = None) -> GmailSyncResult:
        labels = labels or ["INBOX"]
        checkpoint = self.state_store.get_checkpoint(GMAIL_SYNC_CHECKPOINT_KEY)
        dry_run = self.notion_executor.dry_run
        self.event_log.append(
            event_type=EventType.GMAIL_SYNC_STARTED,
            source="gmail",
            source_id="sync",
            data={"labels": labels, "checkpoint": checkpoint, "dry_run": dry_run},
            status=EventStatus.STARTED,
        )
        with self._span(
            "career_ops.gmail_poll",
            checkpoint=checkpoint or "",
            labels=",".join(labels),
            dry_run=dry_run,
        ):
            messages = self.gmail_client.fetch_since(checkpoint, labels)
        result = GmailSyncResult(fetched=len(messages))
        if self.observability is not None:
            self.observability.increment(
                "career_forge.gmail.messages",
                len(messages),
                status="fetched",
            )

        for message in messages:
            if self.state_store.is_processed("gmail", message.message_id):
                result.skipped += 1
                self.event_log.append(
                    event_type=EventType.GMAIL_MESSAGE_SKIPPED,
                    source="gmail",
                    source_id=message.message_id,
                    data={"reason": "already_processed"},
                    status=EventStatus.SKIPPED,
                )
                continue

            try:
                with self._span("career_ops.gmail_message", message_id=message.message_id):
                    execution_succeeded = self._process_message(message, result)
                if not execution_succeeded:
                    continue
                if not dry_run:
                    self.gmail_client.acknowledge_processed(message.message_id)
                    self.state_store.mark_processed("gmail", message.message_id)
                    self.state_store.set_checkpoint(GMAIL_SYNC_CHECKPOINT_KEY, message.message_id)
                result.processed += 1
            except Exception as exc:  # noqa: BLE001 - message-level recovery boundary.
                result.failed += 1
                result.errors.append(str(exc))
                self.event_log.append(
                    event_type=EventType.GMAIL_MESSAGE_CLASSIFICATION_FAILED,
                    source="gmail",
                    source_id=message.message_id,
                    data={"error": str(exc)},
                    status=EventStatus.FAILED,
                    error_details=str(exc),
                    replay_eligible=True,
                )
                self.event_log.append(
                    event_type=EventType.ERROR_RETRY,
                    source="gmail",
                    source_id=message.message_id,
                    data={"error": str(exc)},
                    status=EventStatus.WARNING,
                    error_details=str(exc),
                    replay_eligible=True,
                )
                continue

        self.event_log.append(
            event_type=EventType.GMAIL_SYNC_COMPLETED,
            source="gmail",
            source_id="sync",
            data=result.model_dump(mode="json") | {"event_log_path": str(self.event_log.path)},
            status=EventStatus.COMPLETED if result.failed == 0 else EventStatus.WARNING,
        )
        return result

    def _process_message(self, message: EmailMessage, result: GmailSyncResult) -> bool:
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_SELECTED,
            source="gmail",
            source_id=message.message_id,
            data={"thread_id": message.thread_id, "subject": message.subject},
            correlation_id=message.message_id,
        )
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_RECEIVED,
            source="gmail",
            source_id=message.message_id,
            data={"subject": message.subject, "sender": message.sender},
        )
        plan = self.ingestion_pipeline.plan(message)
        classification_data = {
            "category": plan.classification.category.value,
            "confidence": plan.classification.confidence,
            "requires_human_review": plan.classification.requires_human_review,
            "prompt_version": plan.classification.prompt_version,
            "model_name": plan.classification.model_name,
            "fallback_status": plan.classification.fallback_status,
        }
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_CLASSIFIED,
            source="gmail",
            source_id=message.message_id,
            data=classification_data,
            correlation_id=message.message_id,
            replay_eligible=True,
        )
        self.event_log.append(
            event_type=EventType.EMAIL_CLASSIFIED,
            source="gmail",
            source_id=message.message_id,
            data=classification_data,
            correlation_id=message.message_id,
            replay_eligible=True,
        )
        if plan.classification.requires_human_review:
            result.human_review_required += 1
            result.low_confidence_classifications += 1
            self.event_log.append(
                event_type=EventType.OPERATOR_REVIEW_REQUIRED,
                source="gmail",
                source_id=message.message_id,
                data={"category": plan.classification.category.value},
                status=EventStatus.REVIEW_REQUIRED,
            )
            self.event_log.append(
                event_type=EventType.HUMAN_REVIEW_REQUIRED,
                source="gmail",
                source_id=message.message_id,
                data={"category": plan.classification.category.value},
                status=EventStatus.REVIEW_REQUIRED,
            )
        if plan.interview is not None:
            self.event_log.append(
                event_type=EventType.INTERVIEW_DETECTED,
                source="gmail",
                source_id=message.message_id,
                data={"title": plan.interview.title},
            )
        if plan.follow_up is not None:
            self.event_log.append(
                event_type=EventType.FOLLOW_UP_CREATED,
                source="gmail",
                source_id=message.message_id,
                data={"title": plan.follow_up.title},
            )

        mutations = self.mutation_planner.from_gmail_plan(plan)
        result.mutations_planned += len(mutations)
        notion_result = self.notion_executor.execute(mutations)
        result.mutations_executed += notion_result.executed
        if notion_result.failed:
            errors = [record.error for record in notion_result.records if record.error]
            detail = "; ".join(errors) or "unknown Notion execution error"
            result.failed += 1
            result.errors.append(f"Notion mutation execution failed: {detail}")
            return False
        if self.observability is not None:
            self.observability.increment(
                "career_forge.gmail.messages",
                status="classified",
                low_confidence=plan.classification.requires_human_review,
            )
        return True

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)
