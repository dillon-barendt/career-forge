import json
from pathlib import Path

from benchmark.bench import (
    EmailBenchmarkCase,
    load_cases,
    nearest_rank_p95,
    run_benchmark,
    write_report,
)

from career_ops.ai.deterministic import DeterministicAIService
from career_ops.models import EmailCategory, EmailMessage


class FakeClock:
    def __init__(self, values: list[float]) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


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


def test_benchmark_reports_latency_throughput_and_success_rate() -> None:
    cases = [
        _email_case("case-1", EmailCategory.INTERVIEW_INVITATION),
        _email_case("case-2", EmailCategory.REJECTION),
        _email_case("case-3", EmailCategory.INTERVIEW_INVITATION),
    ]

    report = run_benchmark(
        cases,
        service=DeterministicAIService(),
        clock=FakeClock([0.0, 0.001, 0.001, 0.003, 0.003, 0.013]),
    )

    assert report.total_cases == 3
    assert report.successful_cases == 2
    assert report.success_rate == 2 / 3
    assert report.median_latency_ms == 2.0
    assert report.p95_latency_ms == 10.0
    assert report.throughput_per_second == 3 / 0.013
    assert report.results[1].success is False
    assert report.results[1].error == ("expected Rejection, received Interview Invitation")


def test_default_benchmark_has_exactly_twenty_prompts() -> None:
    cases = load_cases(Path("benchmark/prompts.json"))

    assert len(cases) == 20
    assert len({case.id for case in cases}) == 20
    assert all(case.prompt.strip() for case in cases)


def test_benchmark_report_writes_machine_readable_json(tmp_path) -> None:
    report = run_benchmark(
        [_email_case("case-1", EmailCategory.INTERVIEW_INVITATION)],
        service=DeterministicAIService(),
        clock=FakeClock([0.0, 0.002]),
    )
    output = tmp_path / "results.json"

    write_report(report, output)

    payload = json.loads(output.read_text())
    assert payload["schema_version"] == "1.0"
    assert payload["total_cases"] == 1
    assert payload["results"][0]["case_id"] == "case-1"
