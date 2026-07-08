from career_ops.models.webhooks import WebhookEnvelope


class InlineWebhookQueue:
    """Placeholder queue adapter for later durable/background processing."""

    async def enqueue(self, envelope: WebhookEnvelope) -> None:
        return None
