import json
import os
import tempfile
from pathlib import Path
from typing import Protocol


class InvalidStateError(ValueError):
    """Reports malformed persisted state that cannot be updated safely."""


class StateStore(Protocol):
    def get_checkpoint(self, key: str) -> str | None:
        """Return the last checkpoint for a sync key."""

    def set_checkpoint(self, key: str, value: str) -> None:
        """Persist a checkpoint for a sync key."""

    def is_processed(self, source: str, source_id: str) -> bool:
        """Return whether a source event has already been processed."""

    def mark_processed(self, source: str, source_id: str) -> None:
        """Mark a source event as processed."""

    def finalize_processed(
        self,
        source: str,
        source_id: str,
        *,
        checkpoint_key: str,
        checkpoint_value: str,
    ) -> None:
        """Atomically persist processed state and its corresponding checkpoint."""


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

    def finalize_processed(
        self,
        source: str,
        source_id: str,
        *,
        checkpoint_key: str,
        checkpoint_value: str,
    ) -> None:
        """Persist processed state and checkpoint through one atomic file replacement."""

        data = self._read()
        if "processed" not in data:
            data["processed"] = {}
        processed = data["processed"]
        if not isinstance(processed, dict):
            raise InvalidStateError("State processed must be a dictionary.")
        if source not in processed:
            processed[source] = []
        source_values = processed[source]
        if not isinstance(source_values, list):
            raise InvalidStateError(f"State processed[{source!r}] must be a list.")
        if "checkpoints" not in data:
            data["checkpoints"] = {}
        checkpoints = data["checkpoints"]
        if not isinstance(checkpoints, dict):
            raise InvalidStateError("State checkpoints must be a dictionary.")

        if source_id not in source_values:
            source_values.append(source_id)
        checkpoints[checkpoint_key] = checkpoint_value
        self._write(data)

    def _read(self) -> dict[str, object]:
        if not self.path.exists():
            return {"checkpoints": {}, "processed": {}}
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {"checkpoints": {}, "processed": {}}

    def _write(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary_path.replace(self.path)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise
