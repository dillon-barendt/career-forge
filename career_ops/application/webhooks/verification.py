from typing import Protocol

from career_ops.models.webhooks import WebhookEnvelope, WebhookVerificationResult


class WebhookVerifier(Protocol):
    async def verify(self, envelope: WebhookEnvelope) -> WebhookVerificationResult: ...


class NotConfiguredWebhookVerifier:
    async def verify(self, envelope: WebhookEnvelope) -> WebhookVerificationResult:
        return WebhookVerificationResult(
            status="not_configured",
            reason=f"No verifier is configured for {envelope.project_name}/{envelope.source_name}.",
        )
