from time import perf_counter
from typing import Any

from career_ops.application.webhooks.idempotency import (
    WebhookReceiptStore,
    build_dedupe_key,
    extract_event_id,
    raw_body_sha256,
)
from career_ops.application.webhooks.registry import WebhookSourceRegistry
from career_ops.infrastructure.webhooks.logfire import redact_headers
from career_ops.infrastructure.webhooks.queue import InlineWebhookQueue
from career_ops.models.webhooks import (
    WebhookAck,
    WebhookEnvelope,
    WebhookProcessingResult,
    WebhookRoute,
)
from career_ops.observability import Observability


class WebhookIngestionService:
    def __init__(
        self,
        registry: WebhookSourceRegistry,
        receipt_store: WebhookReceiptStore,
        queue: InlineWebhookQueue | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.registry = registry
        self.receipt_store = receipt_store
        self.queue = queue or InlineWebhookQueue()
        self.observability = observability

    async def ingest(
        self,
        route: WebhookRoute,
        payload: dict[str, Any],
        headers: dict[str, str],
        raw_body: bytes,
    ) -> WebhookProcessingResult:
        started = perf_counter()
        raw_hash = raw_body_sha256(raw_body) if raw_body else None
        safe_headers = redact_headers(headers)
        event_id = extract_event_id(payload, safe_headers)
        dedupe_key = build_dedupe_key(
            route.project_name,
            route.source_name,
            payload,
            safe_headers,
            raw_hash,
        )
        envelope = WebhookEnvelope(
            project_name=route.project_name,
            source_name=route.source_name,
            event_id=event_id,
            dedupe_key=dedupe_key,
            headers=safe_headers,
            payload=payload,
            raw_body_sha256=raw_hash,
        )
        self._info(
            "career_ops.webhooks.received",
            envelope,
            channel="career-forge.webhooks.received",
        )

        with self._span("career_ops.webhooks.ingest", envelope):
            config = self.registry.resolve(route)
            self._info(
                "career_ops.webhooks.route_resolved",
                envelope,
                channel="career-forge.webhooks.received",
                handler_name=config.handler_name,
            )

            verifier = self.registry.verifier_for(route)
            verification = await verifier.verify(envelope)
            envelope.signature_status = verification.status
            self._info(
                "career_ops.webhooks.verification",
                envelope,
                channel=(
                    "career-forge.webhooks.security"
                    if verification.status == "failed"
                    else "career-forge.webhooks.received"
                ),
                verification_reason=verification.reason,
            )

            if await self.receipt_store.exists(dedupe_key):
                envelope.processing_status = "duplicate"
                self._info(
                    "career_ops.webhooks.duplicate",
                    envelope,
                    channel="career-forge.webhooks.received",
                )
                return self._result(envelope, started, duplicate=True)

            await self.receipt_store.record(dedupe_key)
            await self.queue.enqueue(envelope)

            handler = self.registry.handler_for(route)
            try:
                handler_result = await handler.handle(envelope)
            except Exception as exc:
                envelope.processing_status = "failed"
                self._error(
                    "career_ops.webhooks.failed",
                    envelope,
                    channel="career-forge.webhooks.failed",
                    duration_ms=(perf_counter() - started) * 1000,
                    error_type=type(exc).__name__,
                )
                return self._result(envelope, started)

            envelope.processing_status = handler_result.processing_status
            self._info(
                "career_ops.webhooks.handler_completed",
                envelope,
                channel="career-forge.webhooks.received",
                duration_ms=(perf_counter() - started) * 1000,
            )
            return self._result(envelope, started)

    def _result(
        self,
        envelope: WebhookEnvelope,
        started: float,
        *,
        duplicate: bool = False,
    ) -> WebhookProcessingResult:
        return WebhookProcessingResult(
            envelope=envelope,
            ack=WebhookAck(
                accepted=envelope.processing_status != "failed",
                project_name=envelope.project_name,
                source_name=envelope.source_name,
                event_id=envelope.event_id,
                dedupe_key=envelope.dedupe_key,
                processing_status=envelope.processing_status,
            ),
            duplicate=duplicate,
            duration_ms=(perf_counter() - started) * 1000,
        )

    def _span(self, name: str, envelope: WebhookEnvelope):
        if self.observability is None:
            from contextlib import nullcontext

            return nullcontext()
        return self.observability.span(
            name,
            project_name=envelope.project_name,
            source_name=envelope.source_name,
            event_id=envelope.event_id,
            dedupe_key=envelope.dedupe_key,
            signature_status=envelope.signature_status,
            processing_status=envelope.processing_status,
        )

    def _info(self, message: str, envelope: WebhookEnvelope, **attributes: object) -> None:
        if self.observability is not None:
            self.observability.info(message, **self._attributes(envelope, attributes))

    def _error(self, message: str, envelope: WebhookEnvelope, **attributes: object) -> None:
        if self.observability is not None:
            self.observability.error(message, **self._attributes(envelope, attributes))

    def _attributes(
        self,
        envelope: WebhookEnvelope,
        attributes: dict[str, object],
    ) -> dict[str, object]:
        return {
            "project_name": envelope.project_name,
            "source_name": envelope.source_name,
            "event_id": envelope.event_id,
            "dedupe_key": envelope.dedupe_key,
            "signature_status": envelope.signature_status,
            "processing_status": envelope.processing_status,
            **attributes,
        }
