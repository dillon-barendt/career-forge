from typing import Any

import httpx

from career_ops.config import Settings
from career_ops.models import NotionMutation
from career_ops.providers.notion.executor import NotionSchemaValidationResult


class NotionGatewayError(RuntimeError):
    """Raised when the Notion gateway cannot safely execute a mutation."""


class NotionHttpGateway:
    base_url = "https://api.notion.com/v1"

    def __init__(self, settings: Settings) -> None:
        if settings.notion_token is None:
            msg = "CAREER_FORGE_NOTION_TOKEN is required for live Notion sync."
            raise ValueError(msg)
        self.settings = settings
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {settings.notion_token.get_secret_value()}",
                "Notion-Version": settings.notion_version,
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    def upsert(self, mutation: NotionMutation) -> str:
        database_id = self._database_id(mutation.database)
        page_id = self._find_existing_page(database_id, mutation.dedupe_key)
        properties = self._properties(mutation)
        if page_id is None:
            response = self._client.post(
                "/pages",
                json={"parent": {"database_id": database_id}, "properties": properties},
            )
        else:
            response = self._client.patch(f"/pages/{page_id}", json={"properties": properties})
        if response.is_error:
            raise NotionGatewayError(f"Notion API {response.status_code}: {response.text}")
        data = response.json()
        page_id = data.get("id")
        if not isinstance(page_id, str):
            msg = "Notion upsert response did not include a page id."
            raise NotionGatewayError(msg)
        return page_id

    def validate_database_schema(self, database: str) -> NotionSchemaValidationResult:
        database_id = self._database_id(database)
        response = self._client.get(f"/databases/{database_id}")
        if response.is_error:
            return NotionSchemaValidationResult(
                database=database,
                ok=False,
                errors=[f"Notion API {response.status_code}: {response.text}"],
            )
        properties = response.json().get("properties", {})
        if not isinstance(properties, dict):
            return NotionSchemaValidationResult(
                database=database,
                ok=False,
                errors=["Notion database response did not include a properties object."],
            )
        dedupe = properties.get("Dedupe Key")
        if not isinstance(dedupe, dict):
            return NotionSchemaValidationResult(
                database=database,
                ok=False,
                errors=["Database is missing required rich_text property: Dedupe Key"],
            )
        property_type = dedupe.get("type")
        if property_type != "rich_text":
            return NotionSchemaValidationResult(
                database=database,
                ok=False,
                errors=[
                    f"Dedupe Key must be a rich_text property but is {property_type or 'unknown'}."
                ],
            )
        return NotionSchemaValidationResult.valid(database=database)

    def close(self) -> None:
        self._client.close()

    def _find_existing_page(self, database_id: str, dedupe_key: str) -> str | None:
        response = self._client.post(
            f"/databases/{database_id}/query",
            json={
                "filter": {
                    "property": "Dedupe Key",
                    "rich_text": {"equals": dedupe_key},
                }
            },
        )
        if response.status_code == 400:
            return None
        if response.is_error:
            raise NotionGatewayError(f"Notion API {response.status_code}: {response.text}")
        results = response.json().get("results", [])
        if not isinstance(results, list) or not results:
            return None
        page_id = results[0].get("id")
        return page_id if isinstance(page_id, str) else None

    def _properties(self, mutation: NotionMutation) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "Dedupe Key": {"rich_text": [{"text": {"content": mutation.dedupe_key}}]}
        }
        for name, value in mutation.properties.items():
            properties[name] = self._property_value(name, value)
        return properties

    def _property_value(self, name: str, value: object) -> dict[str, Any]:
        if name in {"Title", "Name", "Opportunity"}:
            return {"title": [{"text": {"content": str(value)}}]}
        if name in {"URL", "Job URL"}:
            return {"url": str(value)}
        if name == "Email":
            return {"email": str(value)}
        if name in {"Status", "Priority", "Source"}:
            return {"select": {"name": str(value)}}
        if name in {"Fit Score"} and isinstance(value, int | float):
            return {"number": value}
        if name in {"Due", "Applied On", "Follow Up On"} and value:
            return {"date": {"start": str(value)}}
        return {"rich_text": [{"text": {"content": str(value)}}]}

    def _database_id(self, database: str) -> str:
        mapping = {
            "opportunities": self.settings.opportunities_database_id,
            "companies": self.settings.companies_database_id,
            "contacts": self.settings.contacts_database_id,
            "applications": self.settings.applications_database_id,
            "materials": self.settings.materials_database_id,
            "interviews": self.settings.interviews_database_id,
            "followups": self.settings.followups_database_id,
            "outreach_templates": self.settings.outreach_templates_database_id,
            "research_notes": self.settings.research_notes_database_id,
            "tasks": self.settings.tasks_database_id,
            "weekly_reviews": self.settings.weekly_reviews_database_id,
        }
        database_id = mapping.get(database)
        if database_id is None:
            msg = f"No Notion database id configured for {database!r}."
            raise NotionGatewayError(msg)
        return database_id
