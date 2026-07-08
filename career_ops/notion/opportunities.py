from typing import Any

from career_ops.notion.client import NotionClient
from career_ops.notion.schemas import JobOpportunity


class OpportunityRepository:
    def __init__(self, client: NotionClient, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    async def list_for_review(self) -> list[dict[str, Any]]:
        payload = {
            "filter": {
                "property": "Status",
                "select": {"equals": "new"},
            }
        }
        data = await self.client.query_database(self.database_id, payload)
        results = data.get("results", [])
        return results if isinstance(results, list) else []

    async def create(self, opportunity: JobOpportunity) -> dict[str, Any]:
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": {
                "Title": {"title": [{"text": {"content": opportunity.title}}]},
                "Company": {"rich_text": [{"text": {"content": opportunity.company}}]},
                "Status": {"select": {"name": opportunity.status.value}},
                "Source": {
                    "rich_text": [{"text": {"content": opportunity.source or "manual"}}],
                },
            },
        }
        if opportunity.url is not None:
            payload["properties"]["URL"] = {"url": str(opportunity.url)}
        return await self.client.create_page(payload)
