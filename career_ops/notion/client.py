from collections.abc import Mapping
from typing import Any

import httpx
from career_ops.config import Settings


class NotionClientError(RuntimeError):
    """Raised when Notion returns an error response."""


class NotionClient:
    """Thin async wrapper over the Notion API."""

    base_url = "https://api.notion.com/v1"

    def __init__(self, settings: Settings, client: httpx.AsyncClient | None = None) -> None:
        if settings.notion_token is None:
            msg = "CAREER_OPS_NOTION_TOKEN is required for Notion API calls."
            raise ValueError(msg)

        token = settings.notion_token.get_secret_value()
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": settings.notion_version,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.request(method, path, json=json)
        if response.is_error:
            raise NotionClientError(f"Notion API {response.status_code}: {response.text}")
        data = response.json()
        if not isinstance(data, dict):
            raise NotionClientError("Notion API returned a non-object payload.")
        return data

    async def query_database(
        self,
        database_id: str,
        payload: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return await self.request("POST", f"/databases/{database_id}/query", json=payload or {})

    async def create_page(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await self.request("POST", "/pages", json=payload)

    async def update_page(self, page_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await self.request("PATCH", f"/pages/{page_id}", json=payload)
