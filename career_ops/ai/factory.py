from dataclasses import dataclass, replace

from career_ops.ai.contracts import CareerAIService
from career_ops.ai.mock import MockAIService
from career_ops.ai.pydantic_ai_service import (
    PydanticAIProviderConfiguration,
    PydanticAIService,
)
from career_ops.config import RuntimeMode, Settings, get_settings
from career_ops.observability import Observability


class AIConfigurationError(RuntimeError):
    """Reports invalid real-provider configuration before model execution."""

    def __init__(self, message: str, *, env_var: str) -> None:
        super().__init__(message)
        self.env_var = env_var


@dataclass(frozen=True)
class AIServiceBuildResult:
    """Pairs a provider-agnostic service with its effective reporting metadata."""

    service: CareerAIService
    model_route: str


def build_ai_service(
    settings: Settings | None = None,
    *,
    observability: Observability | None = None,
) -> CareerAIService:
    """Build the configured AI service after validating real-provider credentials."""

    return build_ai_service_with_metadata(
        settings,
        observability=observability,
    ).service


def build_ai_service_with_metadata(
    settings: Settings | None = None,
    *,
    observability: Observability | None = None,
) -> AIServiceBuildResult:
    """Build an AI service and report the same effective route it will execute."""

    resolved = settings or get_settings()
    if resolved.mode is RuntimeMode.MOCK:
        return AIServiceBuildResult(
            service=MockAIService(),
            model_route="mock:deterministic-v1",
        )
    provider_config = resolve_real_provider_configuration(
        resolved,
        observability=observability,
    )
    return AIServiceBuildResult(
        service=PydanticAIService(
            provider_config=provider_config,
            allow_local_fallback=False,
            observability=observability,
        ),
        model_route=_provider_model_route(provider_config),
    )


def resolve_real_provider_configuration(
    settings: Settings,
    *,
    observability: Observability | None = None,
) -> PydanticAIProviderConfiguration:
    """Resolve and validate the live-provider settings shared by setup and runtime."""

    config = PydanticAIProviderConfiguration.from_settings(settings)
    if observability is not None:
        config = replace(
            config,
            gateway_enabled=observability.resolve_bool(
                "career_forge.ai.gateway_enabled",
                config.gateway_enabled,
                targeting_key="career-forge",
            ),
        )
    if not config.model.startswith("openai:"):
        env_var = "CAREER_FORGE_PYDANTIC_AI_MODEL"
        raise AIConfigurationError(
            f"Real mode requires {env_var} to use the supported openai: provider prefix.",
            env_var=env_var,
        )
    if config.gateway_enabled and config.gateway_api_key is None:
        env_var = "CAREER_FORGE_PYDANTIC_AI_GATEWAY_API_KEY"
        raise AIConfigurationError(
            f"Real gateway mode requires {env_var}.",
            env_var=env_var,
        )
    if not config.gateway_enabled and config.openai_api_key is None:
        env_var = "CAREER_FORGE_OPENAI_API_KEY"
        raise AIConfigurationError(
            f"Real OpenAI mode requires {env_var}.",
            env_var=env_var,
        )
    return config


def configured_ai_model_route(
    settings: Settings,
    *,
    observability: Observability | None = None,
) -> str:
    """Describe configured model routing as provider-agnostic reporting metadata."""

    if settings.mode is RuntimeMode.MOCK:
        return "mock:deterministic-v1"
    config = resolve_real_provider_configuration(settings, observability=observability)
    return _provider_model_route(config)


def _provider_model_route(config: PydanticAIProviderConfiguration) -> str:
    """Render provider reporting metadata from an effective validated configuration."""

    if config.gateway_enabled:
        return f"gateway/openai:{config.model.split(':', 1)[1]}"
    return config.model
