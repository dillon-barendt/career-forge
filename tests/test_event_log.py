from career_ops.events.log import EventLog
from career_ops.models import EventType


def test_event_log_appends_and_reads_structured_events(tmp_path) -> None:
    log = EventLog(tmp_path / "events.jsonl")

    event = log.append(
        event_type=EventType.GMAIL_MESSAGE_RECEIVED,
        source="gmail",
        source_id="msg_1",
        data={"subject": "Interview invitation"},
    )

    events = log.read_all()

    assert events == [event]
    assert events[0].event_type == EventType.GMAIL_MESSAGE_RECEIVED
    assert events[0].source_id == "msg_1"
    assert events[0].data["subject"] == "Interview invitation"
