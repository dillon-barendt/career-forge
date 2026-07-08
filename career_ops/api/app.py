from fastapi import FastAPI

from career_ops.api.routes.webhooks import router as webhooks_router
from career_ops.application.webhooks.idempotency import InMemoryWebhookReceiptStore
from career_ops.application.webhooks.registry import WebhookSourceRegistry
from career_ops.application.webhooks.service import WebhookIngestionService
from career_ops.config import Settings, get_settings
from career_ops.observability import Observability


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    observability = Observability(settings)
    observability.configure()
    registry = WebhookSourceRegistry(settings, observability=observability)
    service = WebhookIngestionService(
        registry=registry,
        receipt_store=InMemoryWebhookReceiptStore(),
        observability=observability,
    )

    app = FastAPI(title="Career Forge Webhooks")
    app.state.webhook_service = service
    app.include_router(webhooks_router)
    return app


app = create_app()
