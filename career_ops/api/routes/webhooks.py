from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Request, status

from career_ops.application.webhooks.registry import UnsupportedWebhookSourceError
from career_ops.config import get_settings
from career_ops.models.webhooks import WebhookAck, WebhookRoute

if TYPE_CHECKING:
    from career_ops.application.webhooks.service import WebhookIngestionService

router = APIRouter()


@router.post("/hooks/{project_name}/{source_name}", response_model=WebhookAck)
async def ingest_webhook(
    project_name: str,
    source_name: str,
    request: Request,
) -> WebhookAck:
    settings = get_settings()
    raw_body = await request.body()
    if len(raw_body) > settings.webhooks_max_body_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Webhook payload is too large.",
        )

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook payload must be a JSON object.",
        )

    service: WebhookIngestionService = request.app.state.webhook_service
    try:
        result = await service.ingest(
            WebhookRoute(project_name=project_name, source_name=source_name),
            payload=payload,
            headers=dict(request.headers),
            raw_body=raw_body,
        )
    except UnsupportedWebhookSourceError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if result.ack.processing_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.ack.model_dump(),
        )
    return result.ack
