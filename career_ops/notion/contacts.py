from typing import Any

from career_ops.notion.client import NotionClient
from career_ops.notion.schemas import Contact


class ContactRepository:
    def __init__(self, client: NotionClient, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    async def create(self, contact: Contact) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": contact.name}}]},
            "Notes": {"rich_text": [{"text": {"content": contact.notes}}]},
        }
        if contact.company:
            properties["Company"] = {"rich_text": [{"text": {"content": contact.company}}]}
        if contact.role:
            properties["Role"] = {"rich_text": [{"text": {"content": contact.role}}]}
        if contact.email:
            properties["Email"] = {"email": contact.email}
        if contact.linkedin_url is not None:
            properties["LinkedIn"] = {"url": str(contact.linkedin_url)}
        return await self.client.create_page(
            {"parent": {"database_id": self.database_id}, "properties": properties}
        )
