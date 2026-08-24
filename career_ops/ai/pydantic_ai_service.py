import os
from collections.abc import Iterator
from contextlib import nullcontext
from dataclasses import dataclass, replace
from typing import Any, Protocol

from pydantic import SecretStr

from career_ops.ai.prompts import (
    EMAIL_CLASSIFIER_PROMPT_VERSION,
    OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
    build_email_classifier_prompt,
    build_opportunity_evaluator_prompt,
    parse_email_classifier_output,
    parse_opportunity_evaluator_output,
)
from career_ops.config import Settings, get_settings
from career_ops.models import (
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)
from career_ops.observability import Observability


class AgentRunner(Protocol):
    def run_sync(self, prompt: str) -> Any:
        """Run a Pydantic AI agent and return an object with `.output`."""


@dataclass(frozen=True)
class PydanticAIProviderConfiguration:
    """Carries one resolved live-provider configuration without global rereads."""

    model: str
    openai_api_key: str | None
    gateway_enabled: bool
    gateway_api_key: str | None
    gateway_provider: str
    gateway_route: str | None

    @classmethod
    def from_settings(cls, settings: Settings) -> "PydanticAIProviderConfiguration":
        """Resolve provider values and normalize blank secrets from explicit settings."""

        return cls(
            model=settings.pydantic_ai_model,
            openai_api_key=_secret_value(settings.openai_api_key),
            gateway_enabled=settings.pydantic_ai_gateway_enabled,
            gateway_api_key=_secret_value(settings.pydantic_ai_gateway_api_key),
            gateway_provider=settings.pydantic_ai_gateway_provider,
            gateway_route=settings.pydantic_ai_gateway_route,
        )


class PydanticAIService:
    """Structured AI evaluation facade backed by Pydantic AI agents."""

    def __init__(
        self,
        *,
        model: str | None = None,
        provider_config: PydanticAIProviderConfiguration | None = None,
        email_agent: AgentRunner | None = None,
        opportunity_agent: AgentRunner | None = None,
        allow_local_fallback: bool = True,
        observability: Observability | None = None,
    ) -> None:
        if provider_config is not None and model is not None:
            raise ValueError("Pass either provider_config or model, not both.")
        resolved_config = provider_config or PydanticAIProviderConfiguration.from_settings(
            get_settings()
        )
        if model is not None:
            resolved_config = replace(resolved_config, model=model)
        self.provider_config = resolved_config
        self.model = resolved_config.model
        self.email_agent = email_agent
        self.opportunity_agent = opportunity_agent
        self.allow_local_fallback = allow_local_fallback
        self.observability = observability

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        self._increment_ai_request("email_classifier", EMAIL_CLASSIFIER_PROMPT_VERSION)
        with self._span(
            "career_ops.ai.email_classification",
            agent_name="email_classifier",
            message_id=message.message_id,
            prompt_version=EMAIL_CLASSIFIER_PROMPT_VERSION,
            model=self._agent_model_name(),
            gateway_enabled=self._gateway_enabled(),
        ):
            agent = self.email_agent or self._build_agent(
                output_type=PydanticAIEmailEvaluation,
                name="career_ops_email_classifier",
                instructions=EMAIL_CLASSIFIER_INSTRUCTIONS,
            )
            if agent is None:
                result = self._fallback_email_classification(message)
                self._record_ai_result(
                    "email_classifier",
                    result.confidence_score,
                    fallback=True,
                )
                return result

            try:
                result = agent.run_sync(build_email_classifier_prompt(message))
            except Exception:
                if self.allow_local_fallback:
                    fallback = self._fallback_email_classification(message)
                    self._record_ai_result(
                        "email_classifier",
                        fallback.confidence_score,
                        fallback=True,
                    )
                    return fallback
                raise
            try:
                output = parse_email_classifier_output(result.output)
            except Exception:
                if self.allow_local_fallback:
                    fallback = self._fallback_email_classification(message)
                    self._record_ai_result(
                        "email_classifier",
                        fallback.confidence_score,
                        fallback=True,
                    )
                    return fallback
                raise
            evaluation = output.model_copy(
                update={
                    "prompt_version": EMAIL_CLASSIFIER_PROMPT_VERSION,
                    "model_name": self._agent_model_name(),
                    "fallback_status": "none",
                }
            )
            self._record_ai_result("email_classifier", evaluation.confidence_score)
            return evaluation

    def evaluate_opportunity(self, posting: JobPosting) -> OpportunityEvaluation:
        self._increment_ai_request("opportunity_evaluator", OPPORTUNITY_EVALUATOR_PROMPT_VERSION)
        with self._span(
            "career_ops.ai.opportunity_evaluation",
            agent_name="opportunity_evaluator",
            provider=posting.provider,
            prompt_version=OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
            model=self._agent_model_name(),
            gateway_enabled=self._gateway_enabled(),
        ):
            agent = self.opportunity_agent or self._build_agent(
                output_type=OpportunityEvaluation,
                name="career_ops_opportunity_evaluator",
                instructions=OPPORTUNITY_EVALUATOR_INSTRUCTIONS,
            )
            if agent is None:
                result = self._fallback_opportunity_evaluation(posting)
                self._record_ai_result(
                    "opportunity_evaluator",
                    result.confidence_score,
                    fallback=True,
                )
                return result

            try:
                result = agent.run_sync(build_opportunity_evaluator_prompt(posting))
            except Exception:
                if self.allow_local_fallback:
                    fallback = self._fallback_opportunity_evaluation(posting)
                    self._record_ai_result(
                        "opportunity_evaluator",
                        fallback.confidence_score,
                        fallback=True,
                    )
                    return fallback
                raise
            evaluation = parse_opportunity_evaluator_output(result.output)
            self._record_ai_result("opportunity_evaluator", evaluation.confidence_score)
            return evaluation

    def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
        return self.evaluate_opportunity(posting)

    def _build_agent(
        self,
        *,
        output_type: type[object],
        name: str,
        instructions: str,
    ) -> AgentRunner | None:
        self._ensure_provider_environment()
        try:
            from pydantic_ai import Agent
        except ImportError:
            if self.allow_local_fallback:
                return None
            raise
        try:
            return Agent(
                self._agent_model(),
                name=name,
                instructions=instructions,
                output_type=output_type,
                instrument=True,
            )
        except Exception:
            if self.allow_local_fallback:
                return None
            raise

    def _ensure_provider_environment(self) -> None:
        if self._gateway_enabled():
            if self.provider_config.gateway_api_key is not None:
                os.environ["PYDANTIC_AI_GATEWAY_API_KEY"] = self.provider_config.gateway_api_key
            return

        if not self.model.startswith("openai:"):
            return
        if self.provider_config.openai_api_key is not None:
            os.environ["OPENAI_API_KEY"] = self.provider_config.openai_api_key

    def _gateway_enabled(self) -> bool:
        enabled = self.provider_config.gateway_enabled
        if self.observability is not None:
            return self.observability.resolve_bool(
                "career_forge.ai.gateway_enabled",
                enabled,
                targeting_key="career-forge",
            )
        return enabled

    def _agent_model_name(self) -> str:
        model = self.model
        if not self._gateway_enabled() or not model.startswith("openai:"):
            return model
        return f"gateway/openai:{model.split(':', 1)[1]}"

    def _agent_model(self) -> object:
        if (
            self._gateway_enabled()
            and self.provider_config.gateway_route
            and self.model.startswith("openai:")
        ):
            from pydantic_ai.models.openai import OpenAIChatModel
            from pydantic_ai.providers.gateway import gateway_provider

            provider = gateway_provider(
                self.provider_config.gateway_provider,
                route=self.provider_config.gateway_route,
            )
            return OpenAIChatModel(self.model.split(":", 1)[1], provider=provider)
        return self._agent_model_name()

    def _fallback_email_classification(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        from career_ops.ai.deterministic import DeterministicAIService

        return (
            DeterministicAIService()
            .classify_email(message)
            .model_copy(
                update={"model_name": self._agent_model_name(), "fallback_status": "local_fallback"}
            )
        )

    def _fallback_opportunity_evaluation(self, posting: JobPosting) -> OpportunityEvaluation:
        from career_ops.ai.deterministic import DeterministicAIService

        return DeterministicAIService().evaluate(posting)

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)

    def _increment_ai_request(self, agent_name: str, prompt_version: str) -> None:
        if self.observability is not None:
            self.observability.increment(
                "career_forge.ai.requests",
                agent_name=agent_name,
                prompt_version=prompt_version,
                model=self._agent_model_name(),
                gateway_enabled=self._gateway_enabled(),
            )

    def _record_ai_result(
        self,
        agent_name: str,
        confidence: float,
        *,
        fallback: bool = False,
    ) -> None:
        if self.observability is None:
            return
        self.observability.record(
            "career_forge.ai.confidence",
            confidence,
            agent_name=agent_name,
            fallback=fallback,
        )
        if fallback:
            self.observability.increment("career_forge.ai.fallbacks", agent_name=agent_name)


EMAIL_CLASSIFIER_INSTRUCTIONS = """
Classify a Gmail message for a software engineering job search workflow.
Return only the structured output. Be conservative: uncertain messages require
human review.
"""

OPPORTUNITY_EVALUATOR_INSTRUCTIONS = """
Evaluate a software engineering job opportunity for fit, priority, application
material guidance, and interview preparation. Return only the structured output.
"""


def _secret_value(secret: SecretStr | None) -> str | None:
    """Return a stripped configured secret value or None when it is blank."""

    if secret is None:
        return None
    stripped = secret.get_secret_value().strip()
    return stripped or None
