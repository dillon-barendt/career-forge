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


def build_ai_service(
    settings: Settings | None = None,
    *,
    observability: Observability | None = None,
) -> CareerAIService:
    """Build the configured AI service after validating real-provider credentials."""

    resolved = settings or get_settings()
    if resolved.mode is RuntimeMode.MOCK:
        return MockAIService()
    provider_config = resolve_real_provider_configuration(resolved)
    return PydanticAIService(
        provider_config=provider_config,
        allow_local_fallback=False,
        observability=observability,
    )


def resolve_real_provider_configuration(settings: Settings) -> PydanticAIProviderConfiguration:
    """Resolve and validate the live-provider settings shared by setup and runtime."""

    config = PydanticAIProviderConfiguration.from_settings(settings)
    if not config.model.startswith("openai:"):
        return config
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


def configured_ai_model_route(settings: Settings) -> str:
    """Describe configured model routing as provider-agnostic reporting metadata."""

    if settings.mode is RuntimeMode.MOCK:
        return "mock:deterministic-v1"
    config = PydanticAIProviderConfiguration.from_settings(settings)
    if config.gateway_enabled and config.model.startswith("openai:"):
        return f"gateway/openai:{config.model.split(':', 1)[1]}"
    return config.model
