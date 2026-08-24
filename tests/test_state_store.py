from pathlib import Path

import pytest

from career_ops.state.store import JsonStateStore


def test_atomic_finalization_failure_leaves_processed_and_checkpoint_unchanged(
    tmp_path,
    monkeypatch,
) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    real_replace = Path.replace
    replace_attempts = 0

    def fail_first_replace(src: Path, dst: Path) -> Path:
        nonlocal replace_attempts
        replace_attempts += 1
        if replace_attempts == 1:
            raise OSError("temporary state persistence failure")
        return real_replace(src, dst)

    monkeypatch.setattr(Path, "replace", fail_first_replace)

    with pytest.raises(OSError, match="temporary state persistence failure"):
        store.finalize_processed(
            "gmail",
            "msg-atomic",
            checkpoint_key="gmail:last_message_id",
            checkpoint_value="msg-atomic",
        )

    assert store.is_processed("gmail", "msg-atomic") is False
    assert store.get_checkpoint("gmail:last_message_id") is None

    store.finalize_processed(
        "gmail",
        "msg-atomic",
        checkpoint_key="gmail:last_message_id",
        checkpoint_value="msg-atomic",
    )

    assert store.is_processed("gmail", "msg-atomic") is True
    assert store.get_checkpoint("gmail:last_message_id") == "msg-atomic"


@pytest.mark.parametrize(
    ("initial_state", "error_pattern"),
    [
        (
            '{"checkpoints": {}, "processed": {"gmail": "msg-existing"}}\n',
            r"processed\['gmail'\].*list",
        ),
        (
            '{"checkpoints": [], "processed": {"gmail": []}}\n',
            "checkpoints.*dictionary",
        ),
    ],
)
def test_atomic_finalization_rejects_malformed_nested_state_without_writing(
    tmp_path,
    initial_state: str,
    error_pattern: str,
) -> None:
    state_path = tmp_path / "state.json"
    state_path.write_text(initial_state, encoding="utf-8")
    original_bytes = state_path.read_bytes()
    store = JsonStateStore(state_path)

    with pytest.raises(ValueError, match=error_pattern):
        store.finalize_processed(
            "gmail",
            "msg-new",
            checkpoint_key="gmail:last_message_id",
            checkpoint_value="msg-new",
        )

    assert state_path.read_bytes() == original_bytes
