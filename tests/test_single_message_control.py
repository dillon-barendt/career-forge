import pytest

from career_ops.events.log import EventLog
from career_ops.gmail.single_message import SingleMessageWriteControl
from career_ops.models import EmailMessage, EventType
from career_ops.providers.notion.executor import NotionUpsertExecutor


class FakeGmailClient:
    def __init__(self, message: EmailMessage) -> None:
        self.message = message

    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        return [self.message]

    def fetch_message(self, message_id: str) -> EmailMessage:
        assert message_id == self.message.message_id
        return self.message

    def acknowledge_processed(self, message_id: str) -> None:
        raise AssertionError("single-message control should not acknowledge messages")


class FakeNotionGateway:
    def __init__(self) -> None:
        self.upserted: list[str] = []

    def upsert(self, mutation) -> str:
        self.upserted.append(mutation.dedupe_key)
        return f"page-{len(self.upserted)}"


def _message() -> EmailMessage:
    return EmailMessage(
        message_id="msg_1",
        thread_id="thread_1",
        sender="Sam Recruiter <sam@acme.com>",
        recipients=["dillon.barendt.jobs@gmail.com"],
        subject="Interview invitation for Backend Engineer at Acme",
        body=(
            "We would like to schedule a technical interview for the Backend Engineer "
            "role at Acme next week."
        ),
        received_at="2026-07-07T16:00:00Z",
    )


def test_single_message_control_dry_run_previews_all_mutations(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl")
    control = SingleMessageWriteControl(
        gmail_client=FakeGmailClient(_message()),
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(gateway=None, event_log=event_log, dry_run=True),
    )

    result = control.run(message_id="msg_1")

    assert result.dry_run is True
    assert len(result.mutations) >= 4
    assert result.execution.dry_run == len(result.mutations)
    assert result.execution.executed == 0
    assert any(event.event_type == EventType.EMAIL_CLASSIFIED for event in event_log.read_all())


def test_single_message_control_live_requires_matching_confirmation(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl")
    control = SingleMessageWriteControl(
        gmail_client=FakeGmailClient(_message()),
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=FakeNotionGateway(),
            event_log=event_log,
            dry_run=False,
        ),
    )

    with pytest.raises(ValueError, match="confirm-message-id"):
        control.run(message_id="msg_1", mutation_index=0)


def test_single_message_control_live_executes_one_selected_mutation(tmp_path) -> None:
    event_log = EventLog(tmp_path / "events.jsonl")
    gateway = FakeNotionGateway()
    control = SingleMessageWriteControl(
        gmail_client=FakeGmailClient(_message()),
        event_log=event_log,
        notion_executor=NotionUpsertExecutor(
            gateway=gateway,
            event_log=event_log,
            dry_run=False,
        ),
    )

    result = control.run(message_id="msg_1", mutation_index=0, confirm_message_id="msg_1")

    assert result.dry_run is False
    assert result.selected_mutation_index == 0
    assert result.execution.executed == 1
    assert len(gateway.upserted) == 1
    assert gateway.upserted == [result.mutations[0].dedupe_key]
