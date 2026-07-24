from collections.abc import Mapping

from career_ops.application.webhooks.handlers import (
    GitHubWebhookHandler,
    NotionWebhookHandler,
    WebhookHandler,
)
from career_ops.application.webhooks.verification import (
    NotConfiguredWebhookVerifier,
    WebhookVerifier,
)
from career_ops.config import Settings
from career_ops.models.webhooks import WebhookRoute, WebhookSourceConfig
from career_ops.observability import Observability


class UnsupportedWebhookSourceError(ValueError):
    pass


class WebhookSourceRegistry:
    def __init__(
        self,
        settings: Settings,
        observability: Observability | None = None,
        handlers: Mapping[tuple[str, str], WebhookHandler] | None = None,
        verifiers: Mapping[tuple[str, str], WebhookVerifier] | None = None,
    ) -> None:
        self.settings = settings
        self.observability = observability
        self._configs = self._build_configs(settings)
        self._handlers: dict[tuple[str, str], WebhookHandler] = {
            ("career-forge", "github"): GitHubWebhookHandler(observability),
            ("career-forge", "notion"): NotionWebhookHandler(observability),
        }
        if handlers:
            self._handlers.update(handlers)
        self._verifiers: dict[tuple[str, str], WebhookVerifier] = {
            ("career-forge", "github"): NotConfiguredWebhookVerifier(),
            ("career-forge", "notion"): NotConfiguredWebhookVerifier(),
        }
        if verifiers:
            self._verifiers.update(verifiers)

    def _build_configs(self, settings: Settings) -> dict[tuple[str, str], WebhookSourceConfig]:
        configs: dict[tuple[str, str], WebhookSourceConfig] = {}
        if settings.webhooks_enabled and settings.webhooks_notion_enabled:
            configs[("career-forge", "notion")] = WebhookSourceConfig(
                project_name="career-forge",
                source_name="notion",
                enabled=True,
                verifier_name="notion" if settings.webhooks_notion_secret else None,
                handler_name="notion",
            )
        if settings.webhooks_enabled and settings.webhooks_github_enabled:
            configs[("career-forge", "github")] = WebhookSourceConfig(
                project_name="career-forge",
                source_name="github",
                enabled=True,
                verifier_name="github" if settings.webhooks_github_secret else None,
                handler_name="github",
            )
        return configs

    def resolve(self, route: WebhookRoute) -> WebhookSourceConfig:
        key = (route.project_name, route.source_name)
        config = self._configs.get(key)
        if config is None or not config.enabled:
            raise UnsupportedWebhookSourceError(
                f"Unsupported webhook source: {route.project_name}/{route.source_name}"
            )
        return config

    def handler_for(self, route: WebhookRoute) -> WebhookHandler:
        self.resolve(route)
        return self._handlers[(route.project_name, route.source_name)]

    def verifier_for(self, route: WebhookRoute) -> WebhookVerifier:
        self.resolve(route)
        return self._verifiers.get(
            (route.project_name, route.source_name),
            NotConfiguredWebhookVerifier(),
        )
