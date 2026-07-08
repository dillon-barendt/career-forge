import base64
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Protocol

from career_ops.models import EmailMessage

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


class GmailClient(Protocol):
    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        """Fetch messages newer than or not yet represented by a checkpoint."""

    def fetch_message(self, message_id: str) -> EmailMessage:
        """Fetch one Gmail message by provider message id."""

    def acknowledge_processed(self, message_id: str) -> None:
        """Mark one message processed in the provider."""


class GmailOAuthClient:
    """Gmail API client using OAuth token files."""

    def __init__(
        self,
        *,
        credentials_path: Path,
        token_path: Path,
        processed_label_name: str = "Career Ops/Processed",
    ) -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.processed_label_name = processed_label_name
        self._service: Any | None = None
        self._processed_label_id: str | None = None

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        service = self._gmail_service()
        self._processed_label_id = self._ensure_label(self.processed_label_name)
        response = (
            service.users().messages().list(userId="me", labelIds=labels, maxResults=50).execute()
        )
        message_refs = response.get("messages", [])
        messages: list[EmailMessage] = []
        for ref in message_refs:
            message_id = ref.get("id")
            if not isinstance(message_id, str):
                continue
            if checkpoint is not None and message_id == checkpoint:
                break
            payload = (
                service.users().messages().get(userId="me", id=message_id, format="full").execute()
            )
            messages.append(self._to_email_message(payload))
        return list(reversed(messages))

    def fetch_message(self, message_id: str) -> EmailMessage:
        service = self._gmail_service()
        payload = (
            service.users().messages().get(userId="me", id=message_id, format="full").execute()
        )
        return self._to_email_message(payload)

    def acknowledge_processed(self, message_id: str) -> None:
        if self._processed_label_id is None:
            self._processed_label_id = self._ensure_label(self.processed_label_name)
        service = self._gmail_service()
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"addLabelIds": [self._processed_label_id]},
        ).execute()

    def _gmail_service(self) -> Any:
        if self._service is not None:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError as exc:
            msg = (
                "Gmail OAuth requires google-api-python-client, "
                "google-auth-oauthlib, and google-auth-httplib2."
            )
            raise RuntimeError(msg) from exc

        credentials = None
        if self.token_path.exists():
            credentials = Credentials.from_authorized_user_file(
                str(self.token_path),
                GMAIL_SCOPES,
            )
        if credentials is None or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path),
                    GMAIL_SCOPES,
                )
                credentials = flow.run_local_server(port=0)
            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(credentials.to_json(), encoding="utf-8")

        self._service = build("gmail", "v1", credentials=credentials)
        return self._service

    def _ensure_label(self, label_name: str) -> str:
        service = self._gmail_service()
        response = service.users().labels().list(userId="me").execute()
        for label in response.get("labels", []):
            if label.get("name") == label_name and isinstance(label.get("id"), str):
                return label["id"]
        created = (
            service.users()
            .labels()
            .create(
                userId="me",
                body={
                    "name": label_name,
                    "labelListVisibility": "labelShow",
                    "messageListVisibility": "show",
                },
            )
            .execute()
        )
        label_id = created.get("id")
        if not isinstance(label_id, str):
            msg = f"Could not create Gmail label {label_name!r}."
            raise RuntimeError(msg)
        return label_id

    def _to_email_message(self, payload: dict[str, Any]) -> EmailMessage:
        headers = {
            header.get("name", "").lower(): header.get("value", "")
            for header in payload.get("payload", {}).get("headers", [])
        }
        body = self._extract_body(payload.get("payload", {}))
        received_at = self._received_at(headers.get("date"), payload.get("internalDate"))
        return EmailMessage(
            message_id=payload["id"],
            thread_id=payload.get("threadId", payload["id"]),
            sender=headers.get("from", ""),
            recipients=[headers.get("to", "")],
            subject=headers.get("subject", ""),
            body=body,
            received_at=received_at,
        )

    def _extract_body(self, payload: dict[str, Any]) -> str:
        data = payload.get("body", {}).get("data")
        if isinstance(data, str):
            return self._decode_body(data)
        for part in payload.get("parts", []) or []:
            body = self._extract_body(part)
            if body:
                return body
        return ""

    def _decode_body(self, data: str) -> str:
        padded = data + "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
            "utf-8",
            errors="replace",
        )

    def _received_at(self, date_header: str | None, internal_date: object) -> datetime:
        if date_header:
            parsed = parsedate_to_datetime(date_header)
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
        if isinstance(internal_date, str) and internal_date.isdigit():
            return datetime.fromtimestamp(int(internal_date) / 1000, UTC)
        return datetime.now(UTC)
