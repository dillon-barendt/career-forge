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
        self._metrics: dict[str, Any] = {}
        self._variables: dict[str, Any] = {}

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
        if self.settings.logfire_variables_enabled:
            configure_kwargs["variables"] = logfire.VariablesOptions(
                block_before_first_resolve=False,
            )
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
        if self.settings.logfire_instrument_openai and hasattr(logfire, "instrument_openai"):
            logfire.instrument_openai()
        if self.settings.logfire_instrument_httpx and hasattr(logfire, "instrument_httpx"):
            logfire.instrument_httpx(capture_headers=False)
        if self.settings.logfire_instrument_system_metrics and hasattr(
            logfire,
            "instrument_system_metrics",
        ):
            logfire.instrument_system_metrics()

        self._logfire = logfire
        self._configure_metrics()
        self._configure_variables()

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

    def instrument_fastapi(self, app: object) -> None:
        if self._logfire is not None and hasattr(self._logfire, "instrument_fastapi"):
            self._logfire.instrument_fastapi(
                app,
                capture_headers=False,
                excluded_urls="/healthz",
            )

    def increment(self, name: str, value: int = 1, **attributes: object) -> None:
        metric = self._metrics.get(name)
        if metric is not None and hasattr(metric, "add"):
            metric.add(value, attributes or None)

    def record(self, name: str, value: float, **attributes: object) -> None:
        metric = self._metrics.get(name)
        if metric is not None and hasattr(metric, "record"):
            metric.record(value, attributes or None)

    def resolve_bool(self, name: str, default: bool, **context: str) -> bool:
        variable = self._variables.get(name)
        if variable is None or not hasattr(variable, "get"):
            return default
        try:
            targeting_key = context.get("targeting_key", "career-forge")
            with variable.get(targeting_key=targeting_key) as resolved:
                return bool(resolved.value)
        except Exception:
            return default

    def _configure_metrics(self) -> None:
        if self._logfire is None or not self.settings.logfire_metrics_enabled:
            return
        self._metrics = {
            "career_forge.ai.requests": self._logfire.metric_counter(
                "career_forge.ai.requests",
                unit="1",
                description="AI classification and evaluation requests.",
            ),
            "career_forge.ai.fallbacks": self._logfire.metric_counter(
                "career_forge.ai.fallbacks",
                unit="1",
                description="AI requests served by deterministic local fallback.",
            ),
            "career_forge.ai.confidence": self._logfire.metric_histogram(
                "career_forge.ai.confidence",
                unit="1",
                description="AI confidence scores.",
            ),
            "career_forge.webhooks.received": self._logfire.metric_counter(
                "career_forge.webhooks.received",
                unit="1",
                description="Webhook receipts accepted by route.",
            ),
            "career_forge.webhooks.duration_ms": self._logfire.metric_histogram(
                "career_forge.webhooks.duration_ms",
                unit="ms",
                description="Webhook ingestion duration.",
            ),
            "career_forge.evals.cases": self._logfire.metric_counter(
                "career_forge.evals.cases",
                unit="1",
                description="Evaluation cases executed.",
            ),
            "career_forge.evals.pass_rate": self._logfire.metric_histogram(
                "career_forge.evals.pass_rate",
                unit="1",
                description="Evaluation dataset pass rates.",
            ),
            "career_forge.catalog.items": self._logfire.metric_counter(
                "career_forge.catalog.items",
                unit="1",
                description="Cataloged agents, prompts, LLMs, and providers emitted to Logfire.",
            ),
            "career_forge.gmail.messages": self._logfire.metric_counter(
                "career_forge.gmail.messages",
                unit="1",
                description="Gmail messages fetched, classified, skipped, or failed.",
            ),
            "career_forge.notion.mutations": self._logfire.metric_counter(
                "career_forge.notion.mutations",
                unit="1",
                description=(
                    "Notion mutation planning, schema validation, apply, and failure events."
                ),
            ),
            "career_forge.operator.replay": self._logfire.metric_counter(
                "career_forge.operator.replay",
                unit="1",
                description="Operator replay commands for planned Notion mutations.",
            ),
        }

    def _configure_variables(self) -> None:
        if self._logfire is None or not self.settings.logfire_variables_enabled:
            return
        self._variables = {
            "career_forge.ai.gateway_enabled": self._logfire.var(
                "career_forge.ai.gateway_enabled",
                default=self.settings.pydantic_ai_gateway_enabled,
                description="Route Pydantic AI model calls through Pydantic AI Gateway.",
            ),
            "career_forge.ai.local_fallback_enabled": self._logfire.var(
                "career_forge.ai.local_fallback_enabled",
                default=True,
                description="Allow deterministic local fallback for AI workflows.",
            ),
            "career_forge.webhooks.enabled": self._logfire.var(
                "career_forge.webhooks.enabled",
                default=self.settings.webhooks_enabled,
                description="Enable public webhook ingestion routes.",
            ),
        }
