from typing import Any

import pytest
from career_ops.api.app import create_app
from career_ops.application.webhooks.idempotency import (
    InMemoryWebhookReceiptStore,
    build_dedupe_key,
    raw_body_sha256,
)
from career_ops.application.webhooks.registry import WebhookSourceRegistry
from career_ops.application.webhooks.service import WebhookIngestionService
from career_ops.config import Settings
from career_ops.infrastructure.webhooks.logfire import redact_headers
from career_ops.models.webhooks import WebhookEnvelope, WebhookHandlerResult, WebhookRoute
from fastapi.testclient import TestClient


class RecordingObservability:
    def __init__(self) -> None:
        self.infos: list[tuple[str, dict[str, object]]] = []
        self.errors: list[tuple[str, dict[str, object]]] = []

    def info(self, message: str, **attributes: object) -> None:
        self.infos.append((message, attributes))

    def error(self, message: str, **attributes: object) -> None:
        self.errors.append((message, attributes))

    def increment(self, name: str, value: int = 1, **attributes: object) -> None:
        return None

    def record(self, name: str, value: float, **attributes: object) -> None:
        return None

    def span(self, name: str, **attributes: object):
        class Span:
            def __enter__(self) -> None:
                return None

            def __exit__(self, *args: object) -> None:
                return None

        return Span()


class RaisingHandler:
    async def handle(self, envelope: WebhookEnvelope) -> WebhookHandlerResult:
        raise RuntimeError("handler failed")


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_post_career_forge_notion_accepts_json_payload() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post(
        "/hooks/career-forge/notion",
        json={"id": "evt_123", "type": "page.updated"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["project_name"] == "career-forge"
    assert body["source_name"] == "notion"
    assert body["event_id"] == "evt_123"
    assert body["dedupe_key"] == "career-forge:notion:event:evt_123"
    assert body["processing_status"] == "accepted"


def test_post_career_forge_github_accepts_json_payload() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post(
        "/hooks/career-forge/github",
        json={"action": "opened", "issue": {"number": 123}},
        headers={"X-GitHub-Event": "issues", "X-GitHub-Delivery": "delivery_123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["project_name"] == "career-forge"
    assert body["source_name"] == "github"
    assert body["dedupe_key"].startswith("career-forge:github:")
    assert body["processing_status"] == "accepted"


def test_unsupported_project_source_is_rejected() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post("/hooks/career-forge/linear", json={"id": "evt_123"})

    assert response.status_code == 404
    assert "Unsupported webhook source" in response.json()["detail"]


def test_dedupe_key_is_stable_for_same_payload() -> None:
    payload: dict[str, Any] = {"type": "page.updated", "object": "event"}
    headers = {"x-request-id": "req_123"}
    raw_hash = raw_body_sha256(b'{"object":"event","type":"page.updated"}')

    first = build_dedupe_key("career-forge", "notion", payload, headers, raw_hash)
    second = build_dedupe_key("career-forge", "notion", payload, headers, raw_hash)

    assert first == second


def test_sensitive_headers_are_redacted() -> None:
    headers = {
        "Authorization": "Bearer secret",
        "Cookie": "session=secret",
        "X-Api-Key": "secret",
        "X-Request-Id": "req_123",
    }

    redacted = redact_headers(headers)

    assert redacted["authorization"] == "[redacted]"
    assert redacted["cookie"] == "[redacted]"
    assert redacted["x-api-key"] == "[redacted]"
    assert redacted["x-request-id"] == "req_123"


@pytest.mark.anyio
async def test_missing_verifier_config_produces_not_configured() -> None:
    observability = RecordingObservability()
    service = WebhookIngestionService(
        registry=WebhookSourceRegistry(Settings(), observability=observability),
        receipt_store=InMemoryWebhookReceiptStore(),
        observability=observability,
    )

    result = await service.ingest(
        WebhookRoute(project_name="career-forge", source_name="notion"),
        payload={"id": "evt_123"},
        headers={},
        raw_body=b'{"id":"evt_123"}',
    )

    assert result.envelope.signature_status == "not_configured"


@pytest.mark.anyio
async def test_handler_exception_produces_failed_result_and_logfire_error() -> None:
    observability = RecordingObservability()
    settings = Settings()
    registry = WebhookSourceRegistry(
        settings,
        observability=observability,
        handlers={("career-forge", "notion"): RaisingHandler()},
    )
    service = WebhookIngestionService(
        registry=registry,
        receipt_store=InMemoryWebhookReceiptStore(),
        observability=observability,
    )

    result = await service.ingest(
        WebhookRoute(project_name="career-forge", source_name="notion"),
        payload={"id": "evt_123"},
        headers={},
        raw_body=b'{"id":"evt_123"}',
    )

    assert result.ack.accepted is False
    assert result.ack.processing_status == "failed"
    assert observability.errors
    assert observability.errors[-1][0] == "career_ops.webhooks.failed"
    assert observability.errors[-1][1]["channel"] == "career-forge.webhooks.failed"


def test_route_returns_before_source_specific_work_is_required() -> None:
    client = TestClient(create_app(Settings()))

    response = client.post("/hooks/career-forge/notion", json={"type": "unknown_future_schema"})

    assert response.status_code == 200
    assert response.json()["processing_status"] == "accepted"
