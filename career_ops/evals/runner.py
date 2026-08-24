import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext

from career_ops.ai.contracts import CareerAIService
from career_ops.ai.factory import build_ai_service_with_metadata
from career_ops.ai.prompts import (
    EMAIL_CLASSIFIER_PROMPT_VERSION,
    OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
)
from career_ops.compat import UTC
from career_ops.config import get_settings
from career_ops.models import EmailMessage, JobPosting
from career_ops.observability import Observability


@dataclass
class EvalRunSummary:
    dataset_name: str
    prompt_version: str
    model_route: str
    cases: int
    passed: int
    failed: int

    @property
    def pass_rate(self) -> float:
        if self.cases == 0:
            return 0.0
        return round(self.passed / self.cases, 3)


@dataclass
class ExpectedFields(Evaluator[dict[str, Any], dict[str, Any], dict[str, Any]]):
    def evaluate(self, ctx: EvaluatorContext[dict[str, Any], dict[str, Any], dict[str, Any]]):
        expected = ctx.expected_output or {}
        output = ctx.output
        results: dict[str, bool] = {}
        for key, expected_value in expected.items():
            if key == "minimum_fit_score":
                results[key] = output.get("fit_score", 0) >= expected_value
            elif key == "maximum_fit_score":
                results[key] = output.get("fit_score", 100) <= expected_value
            else:
                results[key] = output.get(key) == expected_value
        return results


class LogfireEvalRunner:
    """Runs typed eval datasets through a provider-agnostic AI service."""

    def __init__(
        self,
        *,
        evals_dir: Path = Path("evals"),
        ai_service: CareerAIService | None = None,
        model_route: str | None = None,
        observability: Observability | None = None,
    ) -> None:
        self.evals_dir = evals_dir
        if ai_service is None:
            settings = get_settings()
            build_result = build_ai_service_with_metadata(
                settings,
                observability=observability,
            )
            ai_service = build_result.service
            model_route = model_route or build_result.model_route
        self.ai_service = ai_service
        self.model_route = model_route or "injected"
        self.observability = observability

    def run_all(self) -> list[EvalRunSummary]:
        return [
            self.run_email_classifier(),
            self.run_opportunity_evaluator(),
        ]

    def run_email_classifier(self) -> EvalRunSummary:
        payload = self._load("email_classifier_cases.json")
        cases = [
            Case(
                name=case["name"],
                inputs=case["inputs"],
                expected_output=case["expected_output"],
                metadata={"prompt_version": payload["prompt_version"]},
                evaluators=(ExpectedFields(),),
            )
            for case in payload["cases"]
        ]
        dataset = Dataset(name=payload["name"], cases=cases)
        dataset.evaluate_sync(
            self._classify_email_case,
            name="career-forge-email-classifier",
            task_name="email_classifier",
            metadata={"prompt_version": EMAIL_CLASSIFIER_PROMPT_VERSION},
            progress=False,
        )
        return self._summarize(payload["name"], payload["prompt_version"], cases)

    def run_opportunity_evaluator(self) -> EvalRunSummary:
        payload = self._load("opportunity_evaluator_cases.json")
        cases = [
            Case(
                name=case["name"],
                inputs=case["inputs"],
                expected_output=case["expected_output"],
                metadata={"prompt_version": payload["prompt_version"]},
                evaluators=(ExpectedFields(),),
            )
            for case in payload["cases"]
        ]
        dataset = Dataset(name=payload["name"], cases=cases)
        dataset.evaluate_sync(
            self._evaluate_opportunity_case,
            name="career-forge-opportunity-evaluator",
            task_name="opportunity_evaluator",
            metadata={"prompt_version": OPPORTUNITY_EVALUATOR_PROMPT_VERSION},
            progress=False,
        )
        return self._summarize(payload["name"], payload["prompt_version"], cases)

    def _classify_email_case(self, inputs: dict[str, Any]) -> dict[str, Any]:
        message = EmailMessage(
            message_id=f"eval:{inputs['subject']}",
            thread_id="eval",
            sender=inputs["sender"],
            recipients=["dillon.barendt.jobs@gmail.com"],
            subject=inputs["subject"],
            body=inputs["body"],
            received_at=datetime.now(UTC),
        )
        result = self.ai_service.classify_email(message)
        return {
            "classification": result.classification.value,
            "confidence_score": result.confidence_score,
            "human_review_required": result.human_review_required,
        }

    def _evaluate_opportunity_case(self, inputs: dict[str, Any]) -> dict[str, Any]:
        posting = JobPosting(
            source_url="https://example.com/eval",
            provider="eval",
            company=inputs["company"],
            role=inputs["role"],
            location=inputs.get("location"),
            compensation=inputs.get("compensation") or None,
            description=inputs["description"],
            apply_url="https://example.com/eval",
        )
        result = self.ai_service.evaluate(posting)
        return {
            "fit_score": result.fit_score,
            "confidence_score": result.confidence_score,
            "suggested_next_action": result.suggested_next_action,
        }

    def _summarize(
        self,
        dataset_name: str,
        prompt_version: str,
        cases: list[Case[dict[str, Any], dict[str, Any], dict[str, Any]]],
    ) -> EvalRunSummary:
        passed = 0
        for case in cases:
            output = (
                self._classify_email_case(case.inputs)
                if "subject" in case.inputs
                else self._evaluate_opportunity_case(case.inputs)
            )
            expected = case.expected_output or {}
            if self._matches_expected(output, expected):
                passed += 1
        summary = EvalRunSummary(
            dataset_name=dataset_name,
            prompt_version=prompt_version,
            model_route=self.model_route,
            cases=len(cases),
            passed=passed,
            failed=len(cases) - passed,
        )
        self._emit_summary(summary)
        return summary

    def _emit_summary(self, summary: EvalRunSummary) -> None:
        if self.observability is None:
            return
        self.observability.info(
            "career_ops.evals.completed",
            dataset_name=summary.dataset_name,
            prompt_version=summary.prompt_version,
            cases=summary.cases,
            passed=summary.passed,
            failed=summary.failed,
            pass_rate=summary.pass_rate,
        )
        self.observability.increment(
            "career_forge.evals.cases",
            summary.cases,
            dataset_name=summary.dataset_name,
            prompt_version=summary.prompt_version,
        )
        self.observability.record(
            "career_forge.evals.pass_rate",
            summary.pass_rate,
            dataset_name=summary.dataset_name,
            prompt_version=summary.prompt_version,
        )

    def _load(self, filename: str) -> dict[str, Any]:
        return json.loads((self.evals_dir / filename).read_text(encoding="utf-8"))

    def _matches_expected(self, output: dict[str, Any], expected: dict[str, Any]) -> bool:
        for key, expected_value in expected.items():
            if key == "minimum_fit_score" and output.get("fit_score", 0) < expected_value:
                return False
            if key == "maximum_fit_score" and output.get("fit_score", 100) > expected_value:
                return False
            if key not in {"minimum_fit_score", "maximum_fit_score"} and (
                output.get(key) != expected_value
            ):
                return False
        return True
