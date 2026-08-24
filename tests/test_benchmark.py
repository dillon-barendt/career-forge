import json
from pathlib import Path

import benchmark.bench as benchmark_module
import pytest
from benchmark.bench import (
    EmailBenchmarkCase,
    load_cases,
    nearest_rank_p95,
    render_human,
    run_benchmark,
    write_report,
)

from career_ops.ai.mock import MockAIService
from career_ops.models import (
    EmailCategory,
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)


class FakeClock:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


class MutableClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _email_case(case_id: str, expected: EmailCategory) -> EmailBenchmarkCase:
    return EmailBenchmarkCase(
        id=case_id,
        prompt="Classify this interview invitation.",
        message=EmailMessage(
            message_id=case_id,
            thread_id=f"thread-{case_id}",
            sender="Recruiter <recruiter@acme.com>",
            recipients=["candidate@example.com"],
            subject="Interview invitation",
            body="Please send availability to schedule the interview.",
            received_at="2026-08-24T12:00:00Z",
        ),
        expected_classification=expected,
    )


def test_nearest_rank_p95_uses_observed_latency() -> None:
    assert nearest_rank_p95([1.0, 2.0, 10.0]) == 10.0


def test_benchmark_reports_required_metrics_and_success_details() -> None:
    cases = [
        _email_case("case-1", EmailCategory.INTERVIEW_INVITATION),
        _email_case("case-2", EmailCategory.REJECTION),
        _email_case("case-3", EmailCategory.INTERVIEW_INVITATION),
    ]

    report = run_benchmark(
        cases,
        service=MockAIService(),
        clock=FakeClock([0.0, 0.001, 0.001, 0.003, 0.003, 0.013]),
    )

    assert report.n == 3
    assert report.success_rate == 2 / 3
    assert report.median_ms == 2.0
    assert report.p95_ms == 10.0
    assert report.throughput_per_min == 3 / 0.013 * 60
    assert report.details[1].prompt_id == "case-2"
    assert report.details[1].success is False
    assert report.details[1].error == "expected Rejection, received Interview Invitation"


def test_default_benchmark_has_exactly_twenty_prompts() -> None:
    cases = load_cases(Path("benchmark/prompts.json"))

    assert len(cases) == 20
    assert len({case.id for case in cases}) == 20
    assert all(case.prompt.strip() for case in cases)


def test_email_benchmark_executes_declared_prompt() -> None:
    case = EmailBenchmarkCase(
        id="prompt-driven",
        prompt="Please send availability so we can schedule your interview.",
        message=EmailMessage(
            message_id="prompt-driven",
            thread_id="thread-prompt-driven",
            sender="Operations <ops@example.com>",
            recipients=["candidate@example.com"],
            subject="Update",
            body="No classification signal is present here.",
            received_at="2026-08-24T12:00:00Z",
        ),
        expected_classification=EmailCategory.INTERVIEW_INVITATION,
    )

    report = run_benchmark([case], service=MockAIService())

    assert report.success_rate == 1.0
    assert report.details[0].success is True


def test_benchmark_stops_clock_before_expectation_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = MutableClock()
    original_validate = benchmark_module._validate_case

    def slow_validation(*args: object, **kwargs: object) -> tuple[str, str | None]:
        clock.advance(1.0)
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(benchmark_module, "_validate_case", slow_validation)

    report = run_benchmark(
        [_email_case("case-1", EmailCategory.INTERVIEW_INVITATION)],
        service=MockAIService(),
        clock=clock,
    )

    assert report.details[0].latency_ms == 0.0


def test_benchmark_excludes_prompt_preparation_from_measured_latency() -> None:
    clock = MutableClock()

    class TimedEmailMessage(EmailMessage):
        def model_copy(
            self,
            *,
            update: dict[str, object] | None = None,
            deep: bool = False,
        ) -> "TimedEmailMessage":
            clock.advance(1.0)
            return super().model_copy(update=update, deep=deep)

    class TimedService:
        def classify_email(self, message: EmailMessage) -> PydanticAIEmailEvaluation:
            clock.advance(0.005)
            return MockAIService().classify_email(message)

        def evaluate(self, posting: JobPosting) -> OpportunityEvaluation:
            raise AssertionError("opportunity evaluation is not used by this case")

    case = EmailBenchmarkCase(
        id="preparation-timing",
        prompt="Classify this interview invitation.",
        message=TimedEmailMessage(
            message_id="preparation-timing",
            thread_id="thread-preparation-timing",
            sender="Recruiter <recruiter@acme.com>",
            recipients=["candidate@example.com"],
            subject="Interview invitation",
            body="Please send availability to schedule the interview.",
            received_at="2026-08-24T12:00:00Z",
        ),
        expected_classification=EmailCategory.INTERVIEW_INVITATION,
    )

    report = run_benchmark([case], service=TimedService(), clock=clock)

    assert report.details[0].latency_ms == 5.0


def test_benchmark_report_writes_machine_readable_json(tmp_path) -> None:
    report = run_benchmark(
        [_email_case("case-1", EmailCategory.INTERVIEW_INVITATION)],
        service=MockAIService(),
        clock=FakeClock([0.0, 0.002]),
    )
    output = tmp_path / "results.json"

    write_report(report, output)

    payload = json.loads(output.read_text())
    assert set(payload) == {
        "n",
        "median_ms",
        "p95_ms",
        "throughput_per_min",
        "success_rate",
        "details",
    }
    assert payload["n"] == 1
    assert set(payload["details"][0]) == {
        "prompt_id",
        "latency_ms",
        "success",
        "error",
    }


def test_human_output_reports_required_metrics_in_prompts_per_minute() -> None:
    report = run_benchmark(
        [_email_case("case-1", EmailCategory.INTERVIEW_INVITATION)],
        service=MockAIService(),
        clock=FakeClock([0.0, 0.002]),
    )

    output = render_human(report)

    assert "n:            1" in output
    assert "success rate: 100.0%" in output
    assert "median:       2.000 ms" in output
    assert "p95:          2.000 ms" in output
    assert "prompts/min" in output
