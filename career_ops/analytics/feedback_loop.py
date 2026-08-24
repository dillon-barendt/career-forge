from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from pydantic import BaseModel, Field

from career_ops.compat import UTC
from career_ops.models import EventType, WorkflowEvent

LOW_CONFIDENCE_THRESHOLD = 0.65
FAILURE_ALERT_THRESHOLD = 3
LOW_CONFIDENCE_SPIKE_RATE = 0.35
SCORING_DRIFT_THRESHOLD = 18.0


class FeedbackAlert(BaseModel):
    name: str
    severity: str
    detail: str
    recommendation: str


class PromptPerformance(BaseModel):
    prompt_version: str
    sample_count: int = 0
    average_confidence: float | None = None
    low_confidence_rate: float = 0.0
    human_review_rate: float = 0.0
    override_count: int = 0
    failure_count: int = 0


class SourceQuality(BaseModel):
    source: str
    applications: int = 0
    responses: int = 0
    interviews: int = 0
    offers: int = 0
    rejections: int = 0
    response_rate: float = 0.0
    interview_conversion_rate: float = 0.0
    offer_rate: float = 0.0
    quality_score: float = 0.0


class FeedbackLoopReport(BaseModel):
    metrics: dict[str, float | int | str] = Field(default_factory=dict)
    recommendation_types: dict[str, int] = Field(default_factory=dict)
    application_outcomes: dict[str, int] = Field(default_factory=dict)
    prompt_performance: list[PromptPerformance] = Field(default_factory=list)
    source_quality: list[SourceQuality] = Field(default_factory=list)
    alerts: list[FeedbackAlert] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)


def build_feedback_loop_report(events: list[WorkflowEvent]) -> FeedbackLoopReport:
    email_events = _events(events, EventType.EMAIL_CLASSIFIED)
    ai_events = _events(events, EventType.AI_EVALUATION_COMPLETED)
    outcome_events = _events(events, EventType.APPLICATION_OUTCOME_RECORDED)
    override_events = _events(events, EventType.HUMAN_OVERRIDE_RECORDED)
    recommendation_events = _events(events, EventType.RECOMMENDATION_ISSUED)
    failures = [
        event
        for event in events
        if event.event_type in {EventType.ERROR_RETRY, EventType.AGENT_FAILURE}
    ]

    confidences = [_float(event.data.get("confidence")) for event in email_events]
    confidences = [value for value in confidences if value is not None]
    low_confidence_count = sum(value < LOW_CONFIDENCE_THRESHOLD for value in confidences)
    fit_scores = [_float(event.data.get("fit_score")) for event in ai_events]
    fit_scores = [value for value in fit_scores if value is not None]

    outcomes = Counter(_normalized_outcome(event.data) for event in outcome_events)
    recommendation_types = Counter(
        _recommendation_type(event.data) for event in [*ai_events, *recommendation_events]
    )
    recommendation_types.pop("", None)

    metrics: dict[str, float | int | str] = {
        "email_classifications": len(email_events),
        "average_email_confidence": round(mean(confidences), 3) if confidences else 0.0,
        "low_confidence_rate": _rate(low_confidence_count, len(confidences)),
        "human_overrides": len(override_events),
        "opportunity_evaluations": len(ai_events),
        "average_fit_score": round(mean(fit_scores), 2) if fit_scores else 0.0,
        "agent_failure_rate": _rate(len(failures), max(len(events), 1)),
        "application_outcomes": len(outcome_events),
        "response_rate": _response_rate(outcomes),
        "interview_conversion_rate": _rate(
            outcomes["interview"] + outcomes["offer"],
            max(outcomes["applied"] + outcomes["submitted"], 1),
        ),
    }

    prompt_performance = _prompt_performance(events, override_events, failures)
    source_quality = _source_quality(outcome_events)
    alerts = _alerts(
        events=events,
        email_events=email_events,
        confidences=confidences,
        failures=failures,
        fit_scores=fit_scores,
        source_quality=source_quality,
    )
    improvement_actions = _improvement_actions(alerts, prompt_performance, source_quality)

    return FeedbackLoopReport(
        metrics=metrics,
        recommendation_types=dict(recommendation_types),
        application_outcomes=dict(outcomes),
        prompt_performance=prompt_performance,
        source_quality=source_quality,
        alerts=alerts,
        improvement_actions=improvement_actions,
    )


def _events(events: list[WorkflowEvent], event_type: EventType) -> list[WorkflowEvent]:
    return [event for event in events if event.event_type == event_type]


def _float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _rate(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return round(float(numerator) / float(denominator), 3)


def _normalized_outcome(data: dict[str, Any]) -> str:
    value = str(data.get("outcome") or data.get("stage") or "").strip().lower()
    if value in {"application confirmation", "submitted", "applied"}:
        return "applied"
    if value in {"response", "responded", "recruiter response"}:
        return "response"
    if value in {"interview invitation", "interview", "interviewing"}:
        return "interview"
    if value in {"offer", "offer / negotiation"}:
        return "offer"
    if value in {"rejected", "rejection", "closed"}:
        return "rejection"
    return value or "unknown"


def _response_rate(outcomes: Counter[str]) -> float:
    responded = (
        outcomes["response"] + outcomes["interview"] + outcomes["offer"] + outcomes["rejection"]
    )
    submitted = outcomes["applied"] + outcomes["submitted"]
    return _rate(responded, max(submitted, 1))


def _recommendation_type(data: dict[str, Any]) -> str:
    value = str(
        data.get("recommendation_type")
        or data.get("recommended_next_action")
        or data.get("suggested_next_action")
        or ""
    ).strip()
    if not value:
        return ""
    return value.split(":", maxsplit=1)[0].split(".", maxsplit=1)[0].strip().lower()


def _prompt_performance(
    events: list[WorkflowEvent],
    overrides: list[WorkflowEvent],
    failures: list[WorkflowEvent],
) -> list[PromptPerformance]:
    buckets: dict[str, list[WorkflowEvent]] = defaultdict(list)
    for event in events:
        prompt_version = event.data.get("prompt_version")
        if isinstance(prompt_version, str) and prompt_version:
            buckets[prompt_version].append(event)

    override_counts = Counter(
        event.data.get("prompt_version")
        for event in overrides
        if isinstance(event.data.get("prompt_version"), str)
    )
    failure_counts = Counter(
        event.data.get("prompt_version")
        for event in failures
        if isinstance(event.data.get("prompt_version"), str)
    )

    rows: list[PromptPerformance] = []
    for prompt_version, prompt_events in sorted(buckets.items()):
        confidences = [_confidence(event) for event in prompt_events]
        confidences = [value for value in confidences if value is not None]
        human_reviews = sum(
            bool(event.data.get("requires_human_review") or event.data.get("human_review_required"))
            for event in prompt_events
        )
        low_confidences = sum(value < LOW_CONFIDENCE_THRESHOLD for value in confidences)
        rows.append(
            PromptPerformance(
                prompt_version=prompt_version,
                sample_count=len(prompt_events),
                average_confidence=round(mean(confidences), 3) if confidences else None,
                low_confidence_rate=_rate(low_confidences, len(confidences)),
                human_review_rate=_rate(human_reviews, len(prompt_events)),
                override_count=override_counts[prompt_version],
                failure_count=failure_counts[prompt_version],
            )
        )
    return rows


def _confidence(event: WorkflowEvent) -> float | None:
    return _float(event.data.get("confidence") or event.data.get("confidence_score"))


def _source_quality(outcome_events: list[WorkflowEvent]) -> list[SourceQuality]:
    buckets: dict[str, Counter[str]] = defaultdict(Counter)
    for event in outcome_events:
        source = str(event.data.get("source") or event.source or "unknown")
        buckets[source][_normalized_outcome(event.data)] += 1

    rows: list[SourceQuality] = []
    for source, outcomes in sorted(buckets.items()):
        applications = outcomes["applied"] + outcomes["submitted"]
        responses = (
            outcomes["response"] + outcomes["interview"] + outcomes["offer"] + outcomes["rejection"]
        )
        interviews = outcomes["interview"] + outcomes["offer"]
        offers = outcomes["offer"]
        response_rate = _rate(responses, max(applications, 1))
        interview_rate = _rate(interviews, max(applications, 1))
        offer_rate = _rate(offers, max(applications, 1))
        quality_score = round((response_rate * 40) + (interview_rate * 40) + (offer_rate * 20), 2)
        rows.append(
            SourceQuality(
                source=source,
                applications=applications,
                responses=responses,
                interviews=interviews,
                offers=offers,
                rejections=outcomes["rejection"],
                response_rate=response_rate,
                interview_conversion_rate=interview_rate,
                offer_rate=offer_rate,
                quality_score=quality_score,
            )
        )
    return sorted(rows, key=lambda row: row.quality_score, reverse=True)


def _alerts(
    *,
    events: list[WorkflowEvent],
    email_events: list[WorkflowEvent],
    confidences: list[float],
    failures: list[WorkflowEvent],
    fit_scores: list[float],
    source_quality: list[SourceQuality],
) -> list[FeedbackAlert]:
    alerts: list[FeedbackAlert] = []
    failure_counts = Counter((event.source, event.source_id) for event in failures)
    repeated_failures = [
        key for key, count in failure_counts.items() if count >= FAILURE_ALERT_THRESHOLD
    ]
    if repeated_failures:
        alerts.append(
            FeedbackAlert(
                name="repeated_classification_or_agent_failures",
                severity="high",
                detail=(
                    f"{len(repeated_failures)} source items failed at least "
                    f"{FAILURE_ALERT_THRESHOLD} times."
                ),
                recommendation=(
                    "Inspect retry events, add eval cases, and require human review for "
                    "matching inputs."
                ),
            )
        )

    low_confidence_count = sum(value < LOW_CONFIDENCE_THRESHOLD for value in confidences)
    if confidences and _rate(low_confidence_count, len(confidences)) >= LOW_CONFIDENCE_SPIKE_RATE:
        alerts.append(
            FeedbackAlert(
                name="low_confidence_ingestion_spike",
                severity="medium",
                detail=(
                    f"{low_confidence_count}/{len(confidences)} email classifications "
                    "were low confidence."
                ),
                recommendation=(
                    "Promote recent low-confidence emails into classifier evals before "
                    "changing automation."
                ),
            )
        )

    for source, name in (("notion", "notion_mutation_failures"), ("gmail", "gmail_sync_failures")):
        source_failures = [event for event in failures if event.source == source]
        if source_failures:
            alerts.append(
                FeedbackAlert(
                    name=name,
                    severity="high",
                    detail=f"{len(source_failures)} {source} failure/retry events detected.",
                    recommendation=(
                        f"Review {source} credentials, rate limits, and failed event payloads."
                    ),
                )
            )

    if _score_drift(fit_scores):
        alerts.append(
            FeedbackAlert(
                name="opportunity_scoring_drift",
                severity="medium",
                detail="Recent fit scores differ materially from the prior baseline.",
                recommendation="Review scoring weights and opportunity evaluator prompt examples.",
            )
        )

    stale_events = [
        event
        for event in events
        if event.event_type == EventType.STALE_OPPORTUNITY_DETECTED
        or _is_stale_opportunity_event(event)
    ]
    if stale_events:
        alerts.append(
            FeedbackAlert(
                name="stale_opportunities",
                severity="medium",
                detail=f"{len(stale_events)} stale opportunity signals detected.",
                recommendation=(
                    "Run daily review and archive, follow up, or re-score stale opportunities."
                ),
            )
        )

    poor_sources = [
        source
        for source in source_quality
        if source.applications >= 3 and source.response_rate < 0.1
    ]
    if poor_sources:
        alerts.append(
            FeedbackAlert(
                name="poor_source_conversion",
                severity="medium",
                detail=", ".join(source.source for source in poor_sources),
                recommendation=(
                    "Reduce effort on poor sources and prioritize recruiter/referral channels."
                ),
            )
        )

    prompt_regressions = [
        event
        for event in _events(events, EventType.PROMPT_EVAL_COMPLETED)
        if _float(event.data.get("pass_rate")) is not None
        and _float(event.data.get("pass_rate")) < 0.8
    ]
    if prompt_regressions:
        alerts.append(
            FeedbackAlert(
                name="prompt_regression",
                severity="high",
                detail=f"{len(prompt_regressions)} prompt eval runs below pass-rate threshold.",
                recommendation="Block prompt rollout and inspect failed eval cases.",
            )
        )

    if email_events and not confidences:
        alerts.append(
            FeedbackAlert(
                name="missing_classification_confidence",
                severity="low",
                detail="Email classification events exist without confidence values.",
                recommendation=(
                    "Verify classifier event payload schema before relying on trend alerts."
                ),
            )
        )

    return alerts


def _score_drift(scores: list[float]) -> bool:
    if len(scores) < 10:
        return False
    midpoint = len(scores) // 2
    prior = scores[:midpoint]
    recent = scores[midpoint:]
    return abs(mean(recent) - mean(prior)) >= SCORING_DRIFT_THRESHOLD


def _is_stale_opportunity_event(event: WorkflowEvent) -> bool:
    if event.event_type not in {
        EventType.NOTION_MUTATION_PLANNED,
        EventType.NOTION_MUTATION_EXECUTED,
    }:
        return False
    updated_at = event.data.get("last_updated")
    if not isinstance(updated_at, str):
        return False
    try:
        parsed = datetime.fromisoformat(updated_at)
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return datetime.now(UTC) - parsed >= timedelta(days=7)


def _improvement_actions(
    alerts: list[FeedbackAlert],
    prompt_performance: list[PromptPerformance],
    source_quality: list[SourceQuality],
) -> list[str]:
    actions = [alert.recommendation for alert in alerts]
    weak_prompts = [
        prompt
        for prompt in prompt_performance
        if prompt.sample_count >= 3
        and (prompt.low_confidence_rate >= LOW_CONFIDENCE_SPIKE_RATE or prompt.override_count > 0)
    ]
    if weak_prompts:
        names = ", ".join(prompt.prompt_version for prompt in weak_prompts)
        actions.append(f"Add recent failures to eval datasets for prompt versions: {names}.")

    if source_quality:
        best = source_quality[0]
        actions.append(
            f"Prefer source '{best.source}' in daily recommendations until conversion changes."
        )
    if not actions:
        actions.append("Keep collecting outcomes; no feedback-loop interventions are required yet.")
    return list(dict.fromkeys(actions))
