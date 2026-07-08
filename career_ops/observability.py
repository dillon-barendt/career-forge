import os
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any

from career_ops.config import Settings


class Observability:
    """Optional Logfire integration with no-op behavior when unavailable."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._logfire: Any | None = None

    def configure(self) -> None:
        try:
            import logfire
        except ImportError:
            return

        token = self._logfire_token()
        configure_kwargs: dict[str, object] = {
            "service_name": self.settings.logfire_service_name,
            "environment": self.settings.logfire_environment,
            "advanced": logfire.AdvancedOptions(base_url=self.settings.logfire_base_url),
        }
        if token:
            configure_kwargs["token"] = token
        else:
            configure_kwargs["send_to_logfire"] = "if-token-present"

        try:
            logfire.configure(**configure_kwargs)
        except Exception:
            if token:
                raise
            return

        logfire.instrument_pydantic_ai(
            include_binary_content=False,
            include_content=False,
        )
        self._logfire = logfire

    def _logfire_token(self) -> str | None:
        if token := os.getenv("LOGFIRE_TOKEN"):
            return token
        if self.settings.logfire_token is not None:
            return self.settings.logfire_token.get_secret_value()
        return None

    @contextmanager
    def span(self, name: str, **attributes: object) -> Iterator[None]:
        if self._logfire is None or not hasattr(self._logfire, "span"):
            with nullcontext():
                yield
            return
        with self._logfire.span(name, **attributes):
            yield

    def info(self, message: str, **attributes: object) -> None:
        if self._logfire is not None:
            self._logfire.info(message, **attributes)

    def error(self, message: str, **attributes: object) -> None:
        if self._logfire is not None:
            self._logfire.error(message, **attributes)
