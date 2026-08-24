from collections.abc import Iterator
from contextlib import nullcontext

from career_ops.automation.gmail_ingestion import (
    GmailClassificationError,
    GmailIngestionPipeline,
)
from career_ops.events.log import EventLog
from career_ops.gmail.client import GmailClient
from career_ops.models import EmailMessage, EventStatus, EventType, GmailSyncResult
from career_ops.observability import Observability
from career_ops.providers.notion.executor import NotionUpsertExecutor
from career_ops.providers.notion.mutations import NotionMutationPlanner
from career_ops.state.store import StateStore

GMAIL_SYNC_CHECKPOINT_KEY = "gmail:last_message_id"


class _GmailMessageStageError(RuntimeError):
    """Carries an unexpected message-processing failure's audit stage and taxonomy."""

    def __init__(self, cause: Exception, *, event_type: EventType, stage: str) -> None:
        super().__init__(str(cause))
        self.cause = cause
        self.event_type = event_type
        self.stage = stage


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
            except _GmailMessageStageError as exc:
                self._record_message_failure(
                    message,
                    result,
                    exc.cause,
                    event_type=exc.event_type,
                    stage=exc.stage,
                )
                break
            except Exception as exc:  # noqa: BLE001 - message-level recovery boundary.
                self._record_message_failure(
                    message,
                    result,
                    exc,
                    event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                    stage="message_processing",
                )
                break
            if not execution_succeeded:
                break
            if not dry_run:
                try:
                    self.gmail_client.acknowledge_processed(message.message_id)
                except Exception as exc:  # noqa: BLE001 - provider recovery boundary.
                    self._record_message_failure(
                        message,
                        result,
                        exc,
                        event_type=EventType.GMAIL_MESSAGE_ACKNOWLEDGEMENT_FAILED,
                        stage="acknowledgement",
                    )
                    break
                try:
                    self.state_store.finalize_processed(
                        "gmail",
                        message.message_id,
                        checkpoint_key=GMAIL_SYNC_CHECKPOINT_KEY,
                        checkpoint_value=message.message_id,
                    )
                except Exception as exc:  # noqa: BLE001 - local recovery boundary.
                    self._record_message_failure(
                        message,
                        result,
                        exc,
                        event_type=EventType.GMAIL_MESSAGE_FINALIZATION_FAILED,
                        stage="local_finalization",
                    )
                    break
            result.processed += 1

        self.event_log.append(
            event_type=EventType.GMAIL_SYNC_COMPLETED,
            source="gmail",
            source_id="sync",
            data=result.model_dump(mode="json") | {"event_log_path": str(self.event_log.path)},
            status=EventStatus.COMPLETED if result.failed == 0 else EventStatus.WARNING,
        )
        return result

    def _record_message_failure(
        self,
        message: EmailMessage,
        result: GmailSyncResult,
        exc: Exception,
        *,
        event_type: EventType,
        stage: str,
    ) -> None:
        """Record an accurately staged per-message failure that remains retryable."""

        error = str(exc)
        result.failed += 1
        result.errors.append(error)
        self.event_log.append(
            event_type=event_type,
            source="gmail",
            source_id=message.message_id,
            data={"error": error, "stage": stage},
            status=EventStatus.FAILED,
            error_details=error,
            replay_eligible=True,
        )
        self.event_log.append(
            event_type=EventType.ERROR_RETRY,
            source="gmail",
            source_id=message.message_id,
            data={"error": error, "stage": stage},
            status=EventStatus.WARNING,
            error_details=error,
            replay_eligible=True,
        )

    def _process_message(self, message: EmailMessage, result: GmailSyncResult) -> bool:
        try:
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
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="event_logging",
            ) from exc

        try:
            plan = self.ingestion_pipeline.plan(message)
        except GmailClassificationError as exc:
            cause = exc.__cause__ if isinstance(exc.__cause__, Exception) else exc
            raise _GmailMessageStageError(
                cause,
                event_type=EventType.GMAIL_MESSAGE_CLASSIFICATION_FAILED,
                stage="classification",
            ) from exc
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="message_planning",
            ) from exc

        try:
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
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="workflow_event_logging",
            ) from exc

        try:
            mutations = self.mutation_planner.from_gmail_plan(plan)
            result.mutations_planned += len(mutations)
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="mutation_planning",
            ) from exc

        try:
            notion_result = self.notion_executor.execute(mutations)
            result.mutations_executed += notion_result.executed
            if notion_result.failed:
                errors = [record.error for record in notion_result.records if record.error]
                detail = "; ".join(errors) or "unknown Notion execution error"
                result.failed += 1
                result.errors.append(f"Notion mutation execution failed: {detail}")
                return False
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="notion_execution",
            ) from exc

        try:
            if self.observability is not None:
                self.observability.increment(
                    "career_forge.gmail.messages",
                    status="classified",
                    low_confidence=plan.classification.requires_human_review,
                )
        except Exception as exc:
            raise _GmailMessageStageError(
                exc,
                event_type=EventType.GMAIL_MESSAGE_PROCESSING_FAILED,
                stage="observability",
            ) from exc

        return True

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)
