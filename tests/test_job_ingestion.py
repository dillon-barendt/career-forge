import pytest

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.ai.mock import MockAIService
from career_ops.ingestion.job_ingestion import JobIngestionPipeline
from career_ops.providers.jobs.base import StaticJobPageFetcher
from career_ops.providers.jobs.registry import default_job_provider_registry

LEVER_HTML = """
<html>
  <head><title>Backend Engineer - Acme</title></head>
  <body>
    <h1>Backend Engineer</h1>
    <div>Acme</div>
    <p>Location: Remote - United States</p>
    <p>Compensation: $150,000 - $190,000</p>
    <p>Employment Type: Full-time</p>
    <p>We need Python, FastAPI, Postgres, observability, and distributed systems.</p>
  </body>
</html>
"""


def test_job_url_ingestion_extracts_posting_and_evaluation() -> None:
    url = "https://jobs.lever.co/acme/123-backend-engineer"
    pipeline = JobIngestionPipeline(
        providers=default_job_provider_registry(),
        fetcher=StaticJobPageFetcher({url: LEVER_HTML}),
    )

    result = pipeline.ingest_url(url)

    assert result.posting.company == "Acme"
    assert result.posting.role == "Backend Engineer"
    assert result.posting.remote_policy == "Remote"
    assert "Python" in result.posting.skills
    assert result.evaluation.fit_score >= 75
    assert result.opportunity.title == "Backend Engineer"
    assert result.opportunity.company == "Acme"
    assert result.recommended_priority == "High"


def test_unsupported_job_url_returns_human_review_result() -> None:
    pipeline = JobIngestionPipeline(
        providers=default_job_provider_registry(),
        fetcher=StaticJobPageFetcher({}),
    )

    result = pipeline.ingest_url("https://example.com/jobs/backend")

    assert result.needs_human_review is True
    assert result.provider_name == "unsupported"
    assert "Unsupported job URL" in result.evaluation.potential_concerns


def test_default_evaluator_uses_configured_mock_service() -> None:
    pipeline = JobIngestionPipeline(fetcher=StaticJobPageFetcher({}))

    assert isinstance(pipeline.evaluator, MockAIService)


def test_fully_injected_pipeline_does_not_load_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_settings_are_loaded() -> None:
        raise AssertionError("fully injected job pipeline loaded settings")

    monkeypatch.setattr(
        "career_ops.ingestion.job_ingestion.get_settings",
        fail_if_settings_are_loaded,
    )
    monkeypatch.setattr(
        "career_ops.ingestion.job_ingestion.build_ai_service",
        fail_if_settings_are_loaded,
    )
    evaluator = DeterministicAIService()

    pipeline = JobIngestionPipeline(
        fetcher=StaticJobPageFetcher({}),
        evaluator=evaluator,
    )

    assert pipeline.evaluator is evaluator
