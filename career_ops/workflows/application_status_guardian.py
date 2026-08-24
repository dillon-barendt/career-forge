import json
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from career_ops.models import EventType, WorkflowEvent
from career_ops.notion.schemas import ApplicationStatus

FindingKind = Literal["stale_application", "missing_data", "status_conflict"]
FindingSeverity = Literal["warning", "review_required"]

OPEN_STATUSES = {
    ApplicationStatus.NEW,
    ApplicationStatus.REVIEWING,
    ApplicationStatus.READY_TO_APPLY,
    ApplicationStatus.APPLIED,
    ApplicationStatus.FOLLOW_UP_DUE,
    ApplicationStatus.INTERVIEWING,
}
TERMINAL_STATUSES = {ApplicationStatus.CLOSED}
IMPORTANT_OUTCOMES = {"offer", "rejection", "rejected", "closed", "withdrawn"}
IMPORTANT_STATUS_HINTS = {"offer", "rejected", "closed", "withdrawn"}


class GuardianApplication(BaseModel):
    """Application health input shaped for Notion reads or local JSON fixtures."""

    application_id: str
    opportunity_title: str
    company: str | None = None
    status: ApplicationStatus = ApplicationStatus.NEW
    source: str | None = None
    applied_on: date | None = None
    follow_up_on: date | None = None
    last_activity_on: date | None = None
    next_action: str | None = None
    status_signals: list[str] = Field(default_factory=list)


class GuardianFinding(BaseModel):
    application_id: str
    kind: FindingKind
    severity: FindingSeverity
    title: str
    detail: str
    recommended_action: str
    requires_human_review: bool = True


class ApplicationStatusHealthReport(BaseModel):
    report_date: date
    applications_checked: int
    findings: list[GuardianFinding] = Field(default_factory=list)

    @property
    def stale_count(self) -> int:
        return _count_findings(self.findings, "stale_application")

    @property
    def missing_data_count(self) -> int:
        return _count_findings(self.findings, "missing_data")

    @property
    def status_conflict_count(self) -> int:
        return _count_findings(self.findings, "status_conflict")

    @property
    def review_required_count(self) -> int:
        return sum(1 for finding in self.findings if finding.requires_human_review)


def load_guardian_applications(path: Path) -> list[GuardianApplication]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload if isinstance(payload, list) else payload.get("applications", [])
    return [GuardianApplication.model_validate(record) for record in records]


def build_application_status_health_report(
    applications: list[GuardianApplication],
    *,
    report_date: date,
    events: list[WorkflowEvent] | None = None,
) -> ApplicationStatusHealthReport:
    outcome_signals = _important_outcome_signals(events or [])
    findings: list[GuardianFinding] = []
    for application in applications:
        findings.extend(_missing_data_findings(application))
        stale_finding = _stale_application_finding(application, report_date)
        if stale_finding is not None:
            findings.append(stale_finding)
        findings.extend(_status_conflict_findings(application, outcome_signals))
    return ApplicationStatusHealthReport(
        report_date=report_date,
        applications_checked=len(applications),
        findings=findings,
    )


def guardian_event_payload(report: ApplicationStatusHealthReport) -> dict[str, object]:
    return {
        "report_date": report.report_date.isoformat(),
        "applications_checked": report.applications_checked,
        "findings_total": len(report.findings),
        "stale_applications": report.stale_count,
        "missing_data": report.missing_data_count,
        "status_conflicts": report.status_conflict_count,
        "review_required": report.review_required_count,
    }


def finding_event_payload(finding: GuardianFinding) -> dict[str, object]:
    return finding.model_dump(mode="json")


def _missing_data_findings(application: GuardianApplication) -> list[GuardianFinding]:
    missing: list[str] = []
    if not _has_text(application.company):
        missing.append("company")
    if not _has_text(application.source):
        missing.append("source")
    if not missing:
        return []
    return [
        GuardianFinding(
            application_id=application.application_id,
            kind="missing_data",
            severity="review_required",
            title=application.opportunity_title,
            detail=f"Missing required application metadata: {', '.join(missing)}.",
            recommended_action="Fill the missing Notion fields before automated routing.",
        )
    ]


def _stale_application_finding(
    application: GuardianApplication,
    report_date: date,
) -> GuardianFinding | None:
    if application.status in TERMINAL_STATUSES:
        return None
    anchor = application.last_activity_on or application.follow_up_on or application.applied_on
    if anchor is None:
        return GuardianFinding(
            application_id=application.application_id,
            kind="stale_application",
            severity="review_required",
            title=application.opportunity_title,
            detail="Open application has no activity, applied, or follow-up date.",
            recommended_action="Review the application and add an auditable next action.",
        )
    days_stale = (report_date - anchor).days
    threshold = _stale_threshold_days(application.status)
    if days_stale < threshold:
        return None
    return GuardianFinding(
        application_id=application.application_id,
        kind="stale_application",
        severity="review_required",
        title=application.opportunity_title,
        detail=f"{application.status.value} has had no activity for {days_stale} days.",
        recommended_action="Human-review the status before follow-up, archive, or status change.",
    )


def _status_conflict_findings(
    application: GuardianApplication,
    outcome_signals: dict[str, set[str]],
) -> list[GuardianFinding]:
    findings: list[GuardianFinding] = []
    signals = {signal.lower() for signal in application.status_signals}
    signals.update(outcome_signals.get(application.application_id, set()))
    important_signals = signals & IMPORTANT_STATUS_HINTS
    if application.status in OPEN_STATUSES and important_signals:
        findings.append(
            GuardianFinding(
                application_id=application.application_id,
                kind="status_conflict",
                severity="review_required",
                title=application.opportunity_title,
                detail=(
                    f"Open status {application.status.value} conflicts with signal(s): "
                    f"{', '.join(sorted(important_signals))}."
                ),
                recommended_action=(
                    "Confirm the important status change manually before updating Notion."
                ),
            )
        )
    if application.status in TERMINAL_STATUSES and (
        application.follow_up_on is not None or _has_text(application.next_action)
    ):
        findings.append(
            GuardianFinding(
                application_id=application.application_id,
                kind="status_conflict",
                severity="review_required",
                title=application.opportunity_title,
                detail="Closed application still has a follow-up date or next action.",
                recommended_action=(
                    "Human-review whether to clear the task or reopen the application."
                ),
            )
        )
    return findings


def _important_outcome_signals(events: list[WorkflowEvent]) -> dict[str, set[str]]:
    signals: dict[str, set[str]] = {}
    for event in events:
        if event.event_type != EventType.APPLICATION_OUTCOME_RECORDED:
            continue
        outcome = event.data.get("outcome")
        if not isinstance(outcome, str):
            continue
        normalized = outcome.lower()
        if normalized not in IMPORTANT_OUTCOMES:
            continue
        if normalized == "rejection":
            normalized = "rejected"
        signals.setdefault(event.source_id, set()).add(normalized)
    return signals


def _stale_threshold_days(status: ApplicationStatus) -> int:
    if status == ApplicationStatus.FOLLOW_UP_DUE:
        return 1
    if status == ApplicationStatus.INTERVIEWING:
        return 7
    return 14


def _has_text(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def _count_findings(findings: list[GuardianFinding], kind: FindingKind) -> int:
    return sum(1 for finding in findings if finding.kind == kind)
