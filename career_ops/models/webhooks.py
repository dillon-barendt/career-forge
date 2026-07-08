from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SignatureStatus = Literal["verified", "unverified", "not_configured", "failed"]
ProcessingStatus = Literal["accepted", "ignored", "duplicate", "failed"]


class WebhookRoute(BaseModel):
    project_name: str = Field(min_length=1)
    source_name: str = Field(min_length=1)


class WebhookEnvelope(BaseModel):
    project_name: str
    source_name: str
    event_id: str | None = None
    dedupe_key: str
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    headers: dict[str, str]
    payload: dict[str, Any]
    raw_body_sha256: str | None = None
    signature_status: SignatureStatus = "not_configured"
    processing_status: ProcessingStatus = "accepted"


class WebhookAck(BaseModel):
    accepted: bool
    project_name: str
    source_name: str
    event_id: str | None = None
    dedupe_key: str
    processing_status: ProcessingStatus


class WebhookProcessingResult(BaseModel):
    envelope: WebhookEnvelope
    ack: WebhookAck
    duplicate: bool = False
    duration_ms: float


class WebhookVerificationResult(BaseModel):
    status: SignatureStatus
    reason: str | None = None


class WebhookSourceConfig(BaseModel):
    project_name: str
    source_name: str
    enabled: bool = True
    verifier_name: str | None = None
    handler_name: str


class WebhookHandlerResult(BaseModel):
    processing_status: ProcessingStatus = "accepted"
    reason: str | None = None


class WebhookReceivedPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
