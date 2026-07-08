import json
import os
from collections.abc import Iterator
from contextlib import nullcontext
from typing import Any, Protocol

from career_ops.config import get_settings
from career_ops.models import (
    EmailCategory,
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)
from career_ops.notion.schemas import JobOpportunity
from career_ops.observability import Observability
from career_ops.scoring.fit_score import score_opportunity
from career_ops.scoring.rules import normalize_text

EMAIL_CLASSIFIER_PROMPT_VERSION = "email-classifier-v1"
OPPORTUNITY_EVALUATOR_PROMPT_VERSION = "opportunity-evaluator-v1"


class AgentRunner(Protocol):
    def run_sync(self, prompt: str) -> Any:
        """Run a Pydantic AI agent and return an object with `.output`."""


class PydanticAIService:
    """Structured AI evaluation facade backed by Pydantic AI agents."""

    def __init__(
        self,
        *,
        model: str = "openai:gpt-5.2",
        email_agent: AgentRunner | None = None,
        opportunity_agent: AgentRunner | None = None,
        allow_local_fallback: bool = True,
        observability: Observability | None = None,
    ) -> None:
        self.model = model
        self.email_agent = email_agent
        self.opportunity_agent = opportunity_agent
        self.allow_local_fallback = allow_local_fallback
        self.observability = observability

    def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        with self._span(
            "career_ops.ai.email_classification",
            message_id=message.message_id,
            prompt_version=EMAIL_CLASSIFIER_PROMPT_VERSION,
        ):
            agent = self.email_agent or self._build_agent(
                output_type=PydanticAIEmailEvaluation,
                name="career_ops_email_classifier",
                instructions=EMAIL_CLASSIFIER_INSTRUCTIONS,
            )
            if agent is None:
                return self._fallback_email_classification(message)

            try:
                result = agent.run_sync(self._email_prompt(message))
            except Exception:
                if self.allow_local_fallback:
                    return self._fallback_email_classification(message)
                raise
            output = result.output
            if not isinstance(output, PydanticAIEmailEvaluation):
                output = PydanticAIEmailEvaluation.model_validate(output)
            return output.model_copy(update={"prompt_version": EMAIL_CLASSIFIER_PROMPT_VERSION})

    def evaluate_opportunity(self, posting: JobPosting) -> OpportunityEvaluation:
        with self._span(
            "career_ops.ai.opportunity_evaluation",
            provider=posting.provider,
            prompt_version=OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
        ):
            agent = self.opportunity_agent or self._build_agent(
                output_type=OpportunityEvaluation,
                name="career_ops_opportunity_evaluator",
                instructions=OPPORTUNITY_EVALUATOR_INSTRUCTIONS,
            )
            if agent is None:
                return self._fallback_opportunity_evaluation(posting)

            try:
                result = agent.run_sync(self._opportunity_prompt(posting))
            except Exception:
                if self.allow_local_fallback:
                    return self._fallback_opportunity_evaluation(posting)
                raise
            output = result.output
            if isinstance(output, OpportunityEvaluation):
                return output
            return OpportunityEvaluation.model_validate(output)

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
                self.model,
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
        if not self.model.startswith("openai:") or os.getenv("OPENAI_API_KEY"):
            return
        settings = get_settings()
        if settings.openai_api_key is not None:
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key.get_secret_value()

    def _email_prompt(self, message: EmailMessage) -> str:
        payload = {
            "prompt_version": EMAIL_CLASSIFIER_PROMPT_VERSION,
            "message_id": message.message_id,
            "thread_id": message.thread_id,
            "sender": message.sender,
            "recipients": message.recipients,
            "subject": message.subject,
            "body": message.body,
            "received_at": message.received_at.isoformat(),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def _opportunity_prompt(self, posting: JobPosting) -> str:
        payload = {
            "prompt_version": OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
            "posting": posting.model_dump(mode="json"),
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    def _fallback_email_classification(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
        text = normalize_text(f"{message.subject} {message.body} {message.sender}")
        category = EmailCategory.COMPANY_COMMUNICATION
        confidence = 0.55
        reason = "Local dry-run fallback could not confidently classify this message."

        if "unsubscribe" in text or "newsletter" in text:
            category = EmailCategory.NEWSLETTER
            confidence = 0.95
            reason = "Newsletter signal detected."
        elif "interview" in text and any(
            term in text for term in ("invite", "schedule", "availability", "available")
        ):
            category = EmailCategory.INTERVIEW_INVITATION
            confidence = 0.9
            reason = "Interview scheduling language detected."
        elif any(term in text for term in ("not moving forward", "unfortunately", "declined")):
            category = EmailCategory.REJECTION
            confidence = 0.9
            reason = "Rejection language detected."
        elif any(term in text for term in ("application received", "thank you for applying")):
            category = EmailCategory.APPLICATION_CONFIRMATION
            confidence = 0.86
            reason = "Application confirmation language detected."
        elif any(term in text for term in ("recruiter", "talent", "opportunity", "role")):
            category = EmailCategory.RECRUITER_OUTREACH
            confidence = 0.72
            reason = "Recruiter or opportunity language detected."

        return PydanticAIEmailEvaluation(
            classification=category,
            confidence_score=confidence,
            executive_summary=f"Email classified as {category.value}.",
            suggested_next_action="Review or process according to classification.",
            human_review_required=confidence < 0.65,
            reasons=[reason],
            prompt_version=EMAIL_CLASSIFIER_PROMPT_VERSION,
        )

    def _fallback_opportunity_evaluation(self, posting: JobPosting) -> OpportunityEvaluation:
        opportunity = JobOpportunity(
            title=posting.role,
            company=posting.company,
            description=posting.description,
            location=posting.location,
            compensation=posting.compensation,
            source=posting.provider,
            tags=[*posting.skills, *posting.tech_stack],
        )
        fit = score_opportunity(opportunity)
        confidence = self._posting_confidence(posting)
        concerns = fit.concerns.copy()
        if not posting.compensation:
            concerns.append("Compensation was not detected in the posting.")
        return OpportunityEvaluation(
            executive_summary=(
                f"{posting.role} at {posting.company} scored {fit.score}/100 "
                "using the local dry-run evaluator."
            ),
            fit_score=fit.score,
            confidence_score=confidence,
            match_analysis=self._match_analysis(fit.score),
            strengths=fit.strengths or ["Posting includes enough detail for review."],
            potential_concerns=concerns,
            missing_qualifications=[],
            resume_suggestions=[f"Mirror the target title: {posting.role}."],
            cover_letter_talking_points=[
                f"Connect prior software engineering impact to {posting.company}."
            ],
            interview_preparation_topics=["Prepare a project walkthrough with tradeoffs."],
            suggested_next_action=fit.recommended_action,
        )

    def _posting_confidence(self, posting: JobPosting) -> float:
        fields = [
            bool(posting.company),
            bool(posting.role),
            bool(posting.description),
            bool(posting.location or posting.remote_policy),
            bool(posting.skills),
            bool(posting.apply_url),
        ]
        return round((sum(fields) / len(fields)) * 100, 2)

    def _match_analysis(self, fit_score: int) -> str:
        if fit_score >= 75:
            return "Strong match. Prioritize application and recruiter outreach."
        if fit_score >= 55:
            return "Possible match. Review missing details before applying."
        return "Weak match. Archive unless strategically valuable."

    def _span(self, name: str, **attributes: object) -> Iterator[None]:
        if self.observability is None:
            return nullcontext()
        return self.observability.span(name, **attributes)


EMAIL_CLASSIFIER_INSTRUCTIONS = """
Classify a Gmail message for a software engineering job search workflow.
Return only the structured output. Be conservative: uncertain messages require
human review.
"""

OPPORTUNITY_EVALUATOR_INSTRUCTIONS = """
Evaluate a software engineering job opportunity for fit, priority, application
material guidance, and interview preparation. Return only the structured output.
"""
