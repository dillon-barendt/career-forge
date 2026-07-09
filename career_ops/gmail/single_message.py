from collections.abc import Iterator
from contextlib import nullcontext

from pydantic import BaseModel

from career_ops.automation.gmail_ingestion import GmailIngestionPipeline
from career_ops.events.log import EventLog
from career_ops.gmail.client import GmailClient
from career_ops.models import (
    EventStatus,
    EventType,
    GmailIngestionPlan,
    NotionExecutionResult,
    NotionMutation,
)
from career_ops.observability import Observability
from career_ops.providers.notion.executor import NotionUpsertExecutor
from career_ops.providers.notion.mutations import NotionMutationPlanner


class SingleMessageWriteResult(BaseModel):
    message_id: str
    dry_run: bool
    classification: str
    confidence: float
    requires_human_review: bool
    mutations: list[NotionMutation]
    selected_mutation_index: int | None = None
    execution: NotionExecutionResult


class SingleMessageWriteControl:
    """Plan or apply exactly one Gmail-derived Notion write."""

    def __init__(
        self,
        *,
        gmail_client: GmailClient,
        event_log: EventLog,
        notion_executor: NotionUpsertExecutor,
        ingestion_pipeline: GmailIngestionPipeline | None = None,
        mutation_planner: NotionMutationPlanner | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.gmail_client = gmail_client
        self.event_log = event_log
        self.notion_executor = notion_executor
        self.ingestion_pipeline = ingestion_pipeline or GmailIngestionPipeline()
        self.mutation_planner = mutation_planner or NotionMutationPlanner()
        self.observability = observability

    def run(
        self,
        *,
        message_id: str,
        mutation_index: int | None = None,
        confirm_message_id: str | None = None,
    ) -> SingleMessageWriteResult:
        with self._span("career_ops.gmail_single_message", message_id=message_id):
            message = self.gmail_client.fetch_message(message_id)
            plan = self.ingestion_pipeline.plan(message)
            self._append_plan_events(plan)
            mutations = self.mutation_planner.from_gmail_plan(plan)
            if not self.notion_executor.dry_run and plan.classification.requires_human_review:
                msg = "Low-confidence single-message plans require human review before live apply."
                raise ValueError(msg)
            selected = self._selected_mutations(
                message_id=message_id,
                mutations=mutations,
                mutation_index=mutation_index,
                confirm_message_id=confirm_message_id,
            )
            execution = self.notion_executor.execute(selected)
            return SingleMessageWriteResult(
                message_id=message.message_id,
                dry_run=self.notion_executor.dry_run,
                classification=plan.classification.category.value,
                confidence=plan.classification.confidence,
                requires_human_review=plan.classification.requires_human_review,
                mutations=mutations,
                selected_mutation_index=mutation_index,
                execution=execution,
            )

    def _selected_mutations(
        self,
        *,
        message_id: str,
        mutations: list[NotionMutation],
        mutation_index: int | None,
        confirm_message_id: str | None,
    ) -> list[NotionMutation]:
        if self.notion_executor.dry_run:
            return mutations
        if confirm_message_id != message_id:
            msg = "Live single-message writes require --confirm-message-id matching the message id."
            raise ValueError(msg)
        if mutation_index is None:
            msg = "Live single-message writes require --mutation-index."
            raise ValueError(msg)
        if mutation_index < 0 or mutation_index >= len(mutations):
            msg = f"Mutation index {mutation_index} is out of range for {len(mutations)} mutations."
            raise ValueError(msg)
        return [mutations[mutation_index]]

    def _append_plan_events(self, plan: GmailIngestionPlan) -> None:
        source_id = plan.dedupe_key.removeprefix("gmail:")
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_SELECTED,
            source="gmail",
            source_id=source_id,
            data={"single_message_control": True},
            correlation_id=source_id,
        )
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_RECEIVED,
            source="gmail",
            source_id=source_id,
            data={"single_message_control": True},
            correlation_id=source_id,
        )
        classification_data = {
            "category": plan.classification.category.value,
            "confidence": plan.classification.confidence,
            "requires_human_review": plan.classification.requires_human_review,
            "prompt_version": plan.classification.prompt_version,
            "single_message_control": True,
        }
        self.event_log.append(
            event_type=EventType.GMAIL_MESSAGE_CLASSIFIED,
            source="gmail",
            source_id=source_id,
            data=classification_data,
            correlation_id=source_id,
            replay_eligible=True,
        )
        self.event_log.append(
            event_type=EventType.EMAIL_CLASSIFIED,
            source="gmail",
            source_id=source_id,
            data=classification_data,
            correlation_id=source_id,
            replay_eligible=True,
        )
        if plan.classification.requires_human_review:
            self.event_log.append(
                event_type=EventType.OPERATOR_REVIEW_REQUIRED,
                source="gmail",
                source_id=source_id,
                data={"category": plan.classification.category.value},
                status=EventStatus.REVIEW_REQUIRED,
            )
            self.event_log.append(
                event_type=EventType.HUMAN_REVIEW_REQUIRED,
                source="gmail",
                source_id=source_id,
                data={"category": plan.classification.category.value},
                status=EventStatus.REVIEW_REQUIRED,
            )
        if plan.interview is not None:
            self.event_log.append(
                event_type=EventType.INTERVIEW_DETECTED,
                source="gmail",
                source_id=source_id,
                data={"title": plan.interview.title},
            )
        if plan.follow_up is not None:
            self.event_log.append(
                event_type=EventType.FOLLOW_UP_CREATED,
                source="gmail",
                source_id=source_id,
                data={"title": plan.follow_up.title},
            )

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)
