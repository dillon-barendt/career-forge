import json
from pathlib import Path
from typing import Protocol


class StateStore(Protocol):
    def get_checkpoint(self, key: str) -> str | None:
        """Return the last checkpoint for a sync key."""

    def set_checkpoint(self, key: str, value: str) -> None:
        """Persist a checkpoint for a sync key."""

    def is_processed(self, source: str, source_id: str) -> bool:
        """Return whether a source event has already been processed."""

    def mark_processed(self, source: str, source_id: str) -> None:
        """Mark a source event as processed."""


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_checkpoint(self, key: str) -> str | None:
        value = self._read().get("checkpoints", {}).get(key)
        return value if isinstance(value, str) else None

    def set_checkpoint(self, key: str, value: str) -> None:
        data = self._read()
        checkpoints = data.setdefault("checkpoints", {})
        if isinstance(checkpoints, dict):
            checkpoints[key] = value
        self._write(data)

    def is_processed(self, source: str, source_id: str) -> bool:
        processed = self._read().get("processed", {})
        if not isinstance(processed, dict):
            return False
        source_values = processed.get(source, [])
        return isinstance(source_values, list) and source_id in source_values

    def mark_processed(self, source: str, source_id: str) -> None:
        data = self._read()
        processed = data.setdefault("processed", {})
        if not isinstance(processed, dict):
            processed = {}
            data["processed"] = processed
        source_values = processed.setdefault(source, [])
        if isinstance(source_values, list) and source_id not in source_values:
            source_values.append(source_id)
        self._write(data)

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"checkpoints": {}, "processed": {}}
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {"checkpoints": {}, "processed": {}}

    def _write(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")
