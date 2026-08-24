import argparse
import math
from collections.abc import Callable, Sequence
from pathlib import Path
from statistics import median
from time import perf_counter
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from career_ops.ai.contracts import CareerAIService
from career_ops.ai.mock import MockAIService
from career_ops.models import (
    EmailCategory,
    EmailMessage,
    JobPosting,
    OpportunityEvaluation,
    PydanticAIEmailEvaluation,
)


class EmailBenchmarkCase(BaseModel):
    """Defines one email-classification prompt and its observable expectation."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["email"] = "email"
    id: str
    prompt: str
    message: EmailMessage
    expected_classification: EmailCategory


class OpportunityBenchmarkCase(BaseModel):
    """Defines one opportunity-evaluation prompt and its observable expectation."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["opportunity"] = "opportunity"
    id: str
    prompt: str
    posting: JobPosting
    min_fit_score: int = Field(ge=0, le=100)
    expected_action: Literal["prioritize", "review", "deprioritize"]


BenchmarkCase = Annotated[
    EmailBenchmarkCase | OpportunityBenchmarkCase,
    Field(discriminator="kind"),
]
CASE_LIST_ADAPTER = TypeAdapter(list[BenchmarkCase])


class BenchmarkDetail(BaseModel):
    """Records one benchmark observation without hiding failed expectations."""

    model_config = ConfigDict(frozen=True)

    prompt_id: str
    latency_ms: float
    success: bool
    error: str | None = None


class BenchmarkReport(BaseModel):
    """Summarizes correctness and latency across a fixed prompt suite."""

    model_config = ConfigDict(frozen=True)

    n: int
    median_ms: float
    p95_ms: float
    throughput_per_min: float
    success_rate: float
    details: list[BenchmarkDetail]


def load_cases(path: Path) -> list[BenchmarkCase]:
    """Loads and validates the versioned benchmark fixture."""

    return CASE_LIST_ADAPTER.validate_json(path.read_text())


def nearest_rank_p95(latencies_ms: list[float]) -> float:
    """Returns the observed value at the nearest-rank 95th percentile."""

    if not latencies_ms:
        return 0.0
    ordered = sorted(latencies_ms)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def run_benchmark(
    cases: Sequence[BenchmarkCase],
    *,
    service: CareerAIService,
    clock: Callable[[], float] = perf_counter,
) -> BenchmarkReport:
    """Measures deterministic agent latency and validates every expected outcome."""

    details: list[BenchmarkDetail] = []
    for case in cases:
        prepared = _prepare_case(case)
        started = clock()
        try:
            evaluation = _invoke_case(prepared, service)
        except Exception as exc:
            latency_ms = round((clock() - started) * 1_000, 6)
            error = f"{type(exc).__name__}: {exc}"
        else:
            latency_ms = round((clock() - started) * 1_000, 6)
            try:
                _, error = _validate_case(case, evaluation)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
        details.append(
            BenchmarkDetail(
                prompt_id=case.id,
                latency_ms=latency_ms,
                success=error is None,
                error=error,
            )
        )

    latencies = [detail.latency_ms for detail in details]
    total_seconds = sum(latencies) / 1_000
    successful = sum(detail.success for detail in details)
    total = len(details)
    return BenchmarkReport(
        n=total,
        median_ms=median(latencies) if latencies else 0.0,
        p95_ms=nearest_rank_p95(latencies),
        throughput_per_min=total / total_seconds * 60 if total_seconds else 0.0,
        success_rate=successful / total if total else 0.0,
        details=details,
    )


def _invoke_case(
    prepared: EmailMessage | JobPosting,
    service: CareerAIService,
) -> PydanticAIEmailEvaluation | OpportunityEvaluation:
    if isinstance(prepared, EmailMessage):
        return service.classify_email(prepared)

    return service.evaluate(prepared)


def _prepare_case(case: BenchmarkCase) -> EmailMessage | JobPosting:
    """Inject the declared prompt before service-call timing begins."""

    if isinstance(case, EmailBenchmarkCase):
        return case.message.model_copy(update={"body": f"{case.prompt}\n\n{case.message.body}"})

    return case.posting.model_copy(
        update={"description": f"{case.prompt}\n\n{case.posting.description}"}
    )


def _validate_case(
    case: BenchmarkCase,
    result: PydanticAIEmailEvaluation | OpportunityEvaluation,
) -> tuple[str, str | None]:
    if isinstance(case, EmailBenchmarkCase):
        if not isinstance(result, PydanticAIEmailEvaluation):
            raise TypeError("email benchmark returned an opportunity evaluation")
        output = result.classification.value
        if result.classification != case.expected_classification:
            return (
                output,
                f"expected {case.expected_classification.value}, received {output}",
            )
        return output, None

    if not isinstance(result, OpportunityEvaluation):
        raise TypeError("opportunity benchmark returned an email evaluation")
    output = f"fit_score={result.fit_score}, action={result.suggested_next_action}"
    if result.fit_score < case.min_fit_score:
        return output, f"expected fit score >= {case.min_fit_score}, received {result.fit_score}"
    if result.suggested_next_action != case.expected_action:
        return (
            output,
            f"expected {case.expected_action}, received {result.suggested_next_action}",
        )
    return output, None


def write_report(report: BenchmarkReport, path: Path) -> None:
    """Persists the complete benchmark report as stable JSON."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n")


def render_human(report: BenchmarkReport) -> str:
    """Renders the benchmark metrics for a reviewer."""

    return "\n".join(
        [
            "CareerForge benchmark",
            f"n:            {report.n}",
            f"success rate: {report.success_rate:.1%}",
            f"median:       {report.median_ms:.3f} ms",
            f"p95:          {report.p95_ms:.3f} ms",
            f"throughput:   {report.throughput_per_min:.1f} prompts/min",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Runs the fixed 20-prompt suite and optionally writes machine-readable results."""

    parser = argparse.ArgumentParser(description="Benchmark CareerForge deterministic agents.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).with_name("prompts.json"),
        help="Path to the benchmark case fixture.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON report path.")
    args = parser.parse_args(argv)
    report = run_benchmark(load_cases(args.cases), service=MockAIService())
    if args.output is not None:
        write_report(report, args.output)
    print(render_human(report))
    return 0 if all(detail.success for detail in report.details) else 1


if __name__ == "__main__":
    raise SystemExit(main())
