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


class GitHubWebhookHandler:
    def __init__(self, observability: Observability | None = None) -> None:
        self.observability = observability

    async def handle(self, envelope: WebhookEnvelope) -> WebhookHandlerResult:
        event_name = envelope.headers.get("x-github-event")
        delivery_id = envelope.headers.get("x-github-delivery")
        if self.observability is not None:
            self.observability.info(
                "career_ops.webhooks.github",
                channel="career-forge.webhooks.github",
                project_name=envelope.project_name,
                source_name=envelope.source_name,
                event_id=envelope.event_id,
                dedupe_key=envelope.dedupe_key,
                signature_status=envelope.signature_status,
                github_event=event_name,
                github_delivery=delivery_id,
            )
        return WebhookHandlerResult(processing_status="accepted")
