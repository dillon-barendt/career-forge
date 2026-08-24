from career_ops.ai.contracts import OpportunityEvaluationService
from career_ops.ai.factory import build_ai_service
from career_ops.ai.prompts import OPPORTUNITY_EVALUATOR_PROMPT_VERSION
from career_ops.config import get_settings
from career_ops.models import JobIngestionResult, JobPosting, OpportunityEvaluation
from career_ops.notion.schemas import JobOpportunity
from career_ops.providers.jobs.base import HttpxJobPageFetcher, JobPageFetcher
from career_ops.providers.jobs.registry import JobProviderRegistry, default_job_provider_registry


class JobIngestionPipeline:
    """Extracts and evaluates job URLs through injected provider boundaries."""

    def __init__(
        self,
        providers: JobProviderRegistry | None = None,
        fetcher: JobPageFetcher | None = None,
        evaluator: OpportunityEvaluationService | None = None,
    ) -> None:
        self.providers = providers or default_job_provider_registry()
        if fetcher is None:
            settings = get_settings()
            fetcher = HttpxJobPageFetcher(timeout=settings.job_fetch_timeout_seconds)
        if evaluator is None:
            evaluator = build_ai_service()
        self.fetcher = fetcher
        self.evaluator = evaluator

    def ingest_url(self, url: str) -> JobIngestionResult:
        provider = self.providers.find(url)
        if provider is None:
            return self._unsupported_result(url)

        html = self.fetcher.fetch(url)
        posting = provider.extract(url, html)
        evaluation = self.evaluator.evaluate(posting)
        opportunity = self._opportunity_from_posting(posting)

        return JobIngestionResult(
            provider_name=provider.name,
            posting=posting,
            evaluation=evaluation,
            opportunity=opportunity,
            recommended_priority=self._priority(evaluation.fit_score),
            recommended_next_action=evaluation.suggested_next_action,
            prompt_version=OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
            needs_human_review=evaluation.confidence_score < 60,
        )

    def _opportunity_from_posting(self, posting: JobPosting) -> JobOpportunity:
        return JobOpportunity(
            title=posting.role,
            company=posting.company,
            description=posting.description,
            url=posting.apply_url or posting.source_url,
            location=posting.location,
            compensation=posting.compensation,
            source=posting.provider,
            tags=[*posting.skills, *posting.tech_stack],
        )

    def _unsupported_result(self, url: str) -> JobIngestionResult:
        posting = JobPosting(
            source_url=url,
            provider="unsupported",
            company="Unknown",
            role="Unsupported job URL",
            description="Unsupported job URL. Paste details manually or add a provider.",
            apply_url=url,
        )
        evaluation = OpportunityEvaluation(
            executive_summary="Unsupported job URL requires human review.",
            fit_score=0,
            confidence_score=0,
            match_analysis="No provider matched this URL, so structured extraction was skipped.",
            strengths=[],
            potential_concerns=["Unsupported job URL"],
            missing_qualifications=[],
            resume_suggestions=[],
            cover_letter_talking_points=[],
            interview_preparation_topics=[],
            suggested_next_action="review",
        )
        return JobIngestionResult(
            provider_name="unsupported",
            posting=posting,
            evaluation=evaluation,
            opportunity=self._opportunity_from_posting(posting),
            recommended_priority="Review",
            recommended_next_action="review",
            prompt_version=OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
            needs_human_review=True,
        )

    def _priority(self, fit_score: int) -> str:
        if fit_score >= 75:
            return "High"
        if fit_score >= 55:
            return "Medium"
        return "Low"
