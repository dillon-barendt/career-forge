from datetime import timezone
from enum import Enum

UTC = timezone.utc


class StrEnum(str, Enum):
    """Provides string-valued enum behavior on every supported Python version."""

    def __str__(self) -> str:
        return str(self.value)
