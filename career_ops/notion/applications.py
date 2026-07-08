from typing import Any

from career_ops.notion.client import NotionClient
from career_ops.notion.schemas import Application


class ApplicationRepository:
    def __init__(self, client: NotionClient, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    async def create(self, application: Application) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "Opportunity": {
                "title": [{"text": {"content": application.opportunity_title}}],
            },
            "Company": {"rich_text": [{"text": {"content": application.company}}]},
            "Status": {"select": {"name": application.status.value}},
        }
        if application.applied_on is not None:
            properties["Applied On"] = {"date": {"start": application.applied_on.isoformat()}}
        if application.follow_up_on is not None:
            properties["Follow Up On"] = {"date": {"start": application.follow_up_on.isoformat()}}
        if application.next_action:
            properties["Next Action"] = {
                "rich_text": [{"text": {"content": application.next_action}}],
            }
        return await self.client.create_page(
            {"parent": {"database_id": self.database_id}, "properties": properties}
        )
