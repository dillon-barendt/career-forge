from typing import Protocol

from career_ops.models.webhooks import WebhookEnvelope, WebhookHandlerResult
from career_ops.observability import Observability


class WebhookHandler(Protocol):
    async def handle(self, envelope: WebhookEnvelope) -> WebhookHandlerResult: ...


class NotionWebhookHandler:
    def __init__(self, observability: Observability | None = None) -> None:
        self.observability = observability

    async def handle(self, envelope: WebhookEnvelope) -> WebhookHandlerResult:
        if self.observability is not None:
            self.observability.info(
                "career_ops.webhooks.notion",
                channel="career-forge.webhooks.notion",
                project_name=envelope.project_name,
                source_name=envelope.source_name,
                event_id=envelope.event_id,
                dedupe_key=envelope.dedupe_key,
                signature_status=envelope.signature_status,
            )
        return WebhookHandlerResult(processing_status="accepted")
