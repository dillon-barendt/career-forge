import hashlib
import json
from typing import Any, Protocol

STABLE_DEDUPE_HEADERS = ("x-notion-event-id", "x-request-id", "x-github-delivery")


def raw_body_sha256(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


def extract_event_id(payload: dict[str, Any], headers: dict[str, str]) -> str | None:
    for key in ("id", "event_id", "eventId"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value

    for key in STABLE_DEDUPE_HEADERS:
        value = headers.get(key)
        if value:
            return value
    return None


def build_dedupe_key(
    project_name: str,
    source_name: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    raw_body_hash: str | None,
) -> str:
    event_id = extract_event_id(payload, headers)
    if event_id:
        return f"{project_name}:{source_name}:event:{event_id}"

    stable_headers = {
        key: headers[key] for key in STABLE_DEDUPE_HEADERS if key in headers and headers[key]
    }
    material = {
        "project_name": project_name,
        "source_name": source_name,
        "raw_body_sha256": raw_body_hash,
        "headers": stable_headers,
    }
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


class WebhookReceiptStore(Protocol):
    async def exists(self, dedupe_key: str) -> bool: ...

    async def record(self, dedupe_key: str) -> None: ...


class InMemoryWebhookReceiptStore:
    """Local-only receipt store; use durable storage before multi-process deployment."""

    def __init__(self) -> None:
        self._dedupe_keys: set[str] = set()

    async def exists(self, dedupe_key: str) -> bool:
        return dedupe_key in self._dedupe_keys

    async def record(self, dedupe_key: str) -> None:
        self._dedupe_keys.add(dedupe_key)
