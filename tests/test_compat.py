from datetime import datetime

from career_ops.compat import UTC, StrEnum


class Example(StrEnum):
    VALUE = "value"


def test_compat_exports_utc_and_string_enum() -> None:
    assert datetime(2026, 8, 24, tzinfo=UTC).isoformat().endswith("+00:00")
    assert str(Example.VALUE) == "value"
    assert Example.VALUE == "value"
