from typing import Any

from career_ops.notion.client import NotionClient
from career_ops.notion.schemas import Company


class CompanyRepository:
    def __init__(self, client: NotionClient, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    async def create(self, company: Company) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "Name": {"title": [{"text": {"content": company.name}}]},
            "Notes": {"rich_text": [{"text": {"content": company.notes}}]},
        }
        if company.website is not None:
            properties["Website"] = {"url": str(company.website)}
        if company.industry:
            properties["Industry"] = {"rich_text": [{"text": {"content": company.industry}}]}
        return await self.client.create_page(
            {"parent": {"database_id": self.database_id}, "properties": properties}
        )
