from typing import Any

from career_ops.notion.client import NotionClient
from career_ops.notion.schemas import MaterialDraft


class MaterialRepository:
    def __init__(self, client: NotionClient, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    async def create(self, draft: MaterialDraft) -> dict[str, Any]:
        return await self.client.create_page(
            {
                "parent": {"database_id": self.database_id},
                "properties": {
                    "Name": {
                        "title": [{"text": {"content": f"{draft.kind}: {draft.opportunity_title}"}}]
                    },
                    "Company": {"rich_text": [{"text": {"content": draft.company}}]},
                    "Kind": {"select": {"name": draft.kind}},
                    "Body": {"rich_text": [{"text": {"content": draft.body[:2000]}}]},
                },
            }
        )
