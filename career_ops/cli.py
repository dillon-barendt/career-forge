import json
import os
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from career_ops.ai.pydantic_ai_service import (
    OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
    PydanticAIService,
)
from career_ops.analytics.feedback_loop import FeedbackLoopReport, build_feedback_loop_report
from career_ops.analytics.weekly import generate_weekly_analytics
from career_ops.cache import LocalCache
from career_ops.config import get_settings
from career_ops.evals.runner import LogfireEvalRunner
from career_ops.events.log import EventLog
from career_ops.external_setup import check_external_setup
from career_ops.gmail.client import GmailOAuthClient
from career_ops.gmail.single_message import SingleMessageWriteControl, SingleMessageWriteResult
from career_ops.gmail.sync import GmailSyncService
from career_ops.ingestion.job_ingestion import JobIngestionPipeline
from career_ops.logfire_catalog import emit_logfire_catalog, full_catalog
from career_ops.materials.cover_letter import build_cover_letter
from career_ops.materials.recruiter_dm import build_recruiter_dm
from career_ops.materials.resume_tailor import build_resume_tailoring_notes
from career_ops.models import (
    EmailMessage,
    EventStatus,
    EventType,
    GmailSyncResult,
    JobPosting,
    NotionMutation,
    WeeklyAnalyticsInput,
)
from career_ops.notion.schemas import JobOpportunity
from career_ops.observability import Observability
from career_ops.operator_loop import NotionReplayError, NotionReplayService
from career_ops.opportunities.lifecycle import (
    ALLOWED_TRANSITIONS,
    OpportunityLifecycleState,
    derive_next_action,
    export_opportunity_lifecycle_mermaid,
)
from career_ops.providers.notion.executor import NotionUpsertExecutor
from career_ops.providers.notion.gateway import NotionHttpGateway
from career_ops.scoring.fit_score import score_opportunity
from career_ops.setup_validation import SetupValidationReport, validate_setup
from career_ops.state.store import JsonStateStore
from career_ops.workflows.application_status_guardian import (
    ApplicationStatusHealthReport,
    build_application_status_health_report,
    finding_event_payload,
    guardian_event_payload,
    load_guardian_applications,
)
from career_ops.workflows.interview_prep import build_interview_prep

app = typer.Typer(help="Career Forge automation.")
setup_app = typer.Typer(help="Validate local operator setup.")
notion_app = typer.Typer(help="Inspect and replay Notion mutation plans.")
draft_app = typer.Typer(help="Generate local application materials.")
app.add_typer(setup_app, name="setup")
app.add_typer(notion_app, name="notion")
app.add_typer(draft_app, name="draft")
console = Console()


def _opportunity_from_args(title: str, company: str, description: str) -> JobOpportunity:
    return JobOpportunity(title=title, company=company, description=description)


@app.command()
def config() -> None:
    """Show local configuration status without printing secrets."""

    settings = get_settings()
    table = Table(title="Career Forge Configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("Notion token", "set" if settings.has_notion_credentials else "missing")
    table.add_row("Opportunities DB", settings.opportunities_database_id or "missing")
    table.add_row("Applications DB", settings.applications_database_id or "missing")
    table.add_row("Companies DB", settings.companies_database_id or "missing")
    table.add_row("Contacts DB", settings.contacts_database_id or "missing")
    table.add_row("Materials DB", settings.materials_database_id or "missing")
    table.add_row("Interviews DB", settings.interviews_database_id or "missing")
    table.add_row("Follow-ups DB", settings.followups_database_id or "missing")
    table.add_row("Outreach Templates DB", settings.outreach_templates_database_id or "missing")
    table.add_row("Research Notes DB", settings.research_notes_database_id or "missing")
    table.add_row("SQLite cache", str(settings.sqlite_path))
    table.add_row("Gmail account", settings.gmail_account)
    table.add_row("AI provider", settings.ai_provider)
    table.add_row("Pydantic AI model", settings.pydantic_ai_model)
    table.add_row(
        "Pydantic AI Gateway",
        "enabled" if settings.pydantic_ai_gateway_enabled else "disabled",
    )
    table.add_row("Gateway provider", settings.pydantic_ai_gateway_provider)
    table.add_row("Gateway route", settings.pydantic_ai_gateway_route or "default")
    table.add_row("OpenAI API key", "set" if settings.openai_api_key else "missing")
    table.add_row(
        "Logfire token",
        "set" if settings.logfire_token or os.getenv("LOGFIRE_TOKEN") else "missing",
    )
    table.add_row("Logfire project", settings.logfire_project)
    table.add_row("Logfire base URL", settings.logfire_base_url)
    table.add_row("Logfire service", settings.logfire_service_name)
    table.add_row("Logfire metrics", "enabled" if settings.logfire_metrics_enabled else "disabled")
    table.add_row(
        "Logfire variables",
        "enabled" if settings.logfire_variables_enabled else "disabled",
    )
    table.add_row("Event log", str(settings.event_log_path))
    table.add_row("State path", str(settings.state_path))
    console.print(table)


@app.command("check-setup")
def check_setup() -> None:
    """Check local external credentials without printing secret values."""

    report = check_external_setup(get_settings())
    table = Table(title="External Setup")
    table.add_column("Integration")
    table.add_column("Ready")
    table.add_column("Detail")
    for item in report.items:
        table.add_row(item.name, "yes" if item.ready else "no", item.detail)
    console.print(table)


@setup_app.command("validate")
def setup_validate() -> None:
    """Validate local operator configuration without printing secrets."""

    report = validate_setup(get_settings())
    _print_setup_validation(report)


@app.command()
def init_cache() -> None:
    """Create the local SQLite cache file."""

    settings = get_settings()
    cache = LocalCache(settings.sqlite_path)
    cache.initialize()
    console.print(f"Initialized cache at {settings.sqlite_path}")


@app.command()
def score(
    title: Annotated[str, typer.Option()],
    company: Annotated[str, typer.Option()],
    description: Annotated[str, typer.Option()] = "",
) -> None:
    """Score one opportunity from CLI input."""

    opportunity = _opportunity_from_args(title, company, description)
    result = score_opportunity(opportunity)
    console.print_json(json.dumps(result.model_dump()))


@app.command("opportunity-lifecycle")
def opportunity_lifecycle(
    mermaid: Annotated[
        bool,
        typer.Option("--mermaid", help="Print the pydantic-graph Mermaid state diagram."),
    ] = False,
) -> None:
    """Show the reusable opportunity schema lifecycle."""

    if mermaid:
        console.print(export_opportunity_lifecycle_mermaid(), markup=False)
        return

    table = Table(title="Opportunity Lifecycle")
    table.add_column("State")
    table.add_column("Next Action")
    table.add_column("Allowed Transitions")
    for state in OpportunityLifecycleState:
        allowed = ", ".join(next_state.value for next_state in ALLOWED_TRANSITIONS[state]) or "none"
        table.add_row(state.value, derive_next_action(state), allowed)
    console.print(table)


@app.command("ingest-url")
def ingest_url(url: Annotated[str, typer.Argument()]) -> None:
    """Ingest and evaluate a supported job posting URL."""

    settings = get_settings()
    observability = _observability()
    result = JobIngestionPipeline(
        evaluator=PydanticAIService(
            model=settings.pydantic_ai_model,
            observability=observability,
        )
    ).ingest_url(url)
    EventLog(settings.event_log_path).append(
        event_type=EventType.AI_EVALUATION_COMPLETED,
        source=result.posting.provider,
        source_id=str(result.posting.source_url),
        data={
            "fit_score": result.evaluation.fit_score,
            "confidence_score": result.evaluation.confidence_score,
            "provider": result.provider_name,
            "source": result.posting.provider,
            "recommended_next_action": result.recommended_next_action,
            "recommendation_type": result.recommended_priority.lower(),
            "prompt_version": result.prompt_version,
            "human_review_required": result.needs_human_review,
        },
    )
    table = Table(title="Job URL Ingestion")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Provider", result.provider_name)
    table.add_row("Company", result.posting.company)
    table.add_row("Role", result.posting.role)
    table.add_row("Fit Score", str(result.evaluation.fit_score))
    table.add_row("Confidence", f"{result.evaluation.confidence_score:.0f}")
    table.add_row("Priority", result.recommended_priority)
    table.add_row("Next Action", result.recommended_next_action)
    table.add_row("Human Review", "yes" if result.needs_human_review else "no")
    console.print(table)


@app.command("ingest-gmail")
def ingest_gmail(
    dry_run: Annotated[bool, typer.Option(help="Plan writes without mutating Notion.")] = True,
) -> None:
    """Poll Gmail, classify messages, and plan or execute Notion mutations."""

    result, event_log_path = _run_gmail_sync(dry_run=dry_run)
    _print_gmail_sync_result(result, dry_run=dry_run, event_log_path=event_log_path)


@app.command("ingest-gmail-message")
def ingest_gmail_message(
    message_id: Annotated[str, typer.Argument(help="Exact Gmail message id to inspect.")],
    dry_run: Annotated[bool, typer.Option(help="Plan writes without mutating Notion.")] = True,
    mutation_index: Annotated[
        int | None,
        typer.Option(help="Required for live mode; applies only this one mutation."),
    ] = None,
    confirm_message_id: Annotated[
        str | None,
        typer.Option(help="Required for live mode; must exactly match MESSAGE_ID."),
    ] = None,
) -> None:
    """Inspect or apply one Gmail message without running broad inbox sync."""

    settings = get_settings()
    observability = _observability()
    event_log = EventLog(settings.event_log_path)
    executor = NotionUpsertExecutor(
        gateway=None if dry_run else NotionHttpGateway(settings),
        event_log=event_log,
        dry_run=dry_run,
        observability=observability,
    )
    control = SingleMessageWriteControl(
        gmail_client=_gmail_client_for_message(),
        event_log=event_log,
        notion_executor=executor,
        observability=observability,
    )
    try:
        result = control.run(
            message_id=message_id,
            mutation_index=mutation_index,
            confirm_message_id=confirm_message_id,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    _print_single_message_result(result)


@app.command("sync-notion")
def sync_notion(
    dry_run: Annotated[bool, typer.Option(help="Verify Notion sync wiring without writes.")] = True,
) -> None:
    """Verify Notion sync wiring; queued mutation replay can be added safely later."""

    settings = get_settings()
    observability = _observability()
    executor = NotionUpsertExecutor(
        gateway=None if dry_run else NotionHttpGateway(settings),
        event_log=EventLog(settings.event_log_path),
        dry_run=dry_run,
        observability=observability,
    )
    result = executor.execute([])
    table = Table(title="Notion Sync")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Executed", str(result.executed))
    table.add_row("Dry run", "yes" if dry_run else "no")
    table.add_row("Pending replay queue", "0")
    console.print(table)


@notion_app.command("plan")
def notion_plan(
    latest: Annotated[
        bool,
        typer.Option("--latest", help="Inspect the latest planned Notion mutation."),
    ] = False,
    event_id: Annotated[
        str | None,
        typer.Option("--event-id", help="Inspect one planned mutation event id."),
    ] = None,
) -> None:
    """Inspect a replayable Notion mutation plan without writing to Notion."""

    if not latest and event_id is None:
        raise typer.BadParameter("Use --latest or --event-id.")
    service = _notion_replay_service(dry_run=True)
    try:
        inspection = (
            service.inspect_event(event_id)
            if event_id is not None
            else service.inspect_latest_plan()
        )
    except NotionReplayError as exc:
        raise typer.BadParameter(str(exc)) from exc
    _print_notion_plan(inspection.event.event_id, inspection.mutation, inspection.replay_eligible)


@notion_app.command("apply")
def notion_apply(
    latest: Annotated[
        bool,
        typer.Option("--latest", help="Apply the latest unapplied Notion mutation plan."),
    ] = False,
    event_id: Annotated[
        str | None,
        typer.Option("--event-id", help="Apply one planned mutation event id."),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option(help="Preview the apply without writing to Notion.")
    ] = True,
    confirm: Annotated[
        bool,
        typer.Option("--confirm", help="Required for live apply and review-required plans."),
    ] = False,
) -> None:
    """Replay one planned Notion mutation with dry-run as the default."""

    if not latest and event_id is None:
        raise typer.BadParameter("Use --latest or --event-id.")
    service = _notion_replay_service(dry_run=dry_run)
    try:
        result = (
            service.apply_event(event_id, dry_run=dry_run, confirm=confirm)
            if event_id is not None
            else service.apply_latest(dry_run=dry_run, confirm=confirm)
        )
    except (NotionReplayError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc
    _print_notion_apply_result(result)


@app.command("run-once")
def run_once(
    dry_run: Annotated[bool, typer.Option(help="Run the operator loop without writes.")] = True,
    apply_reviewed: Annotated[
        bool,
        typer.Option(help="Reserved for explicitly reviewed mutation plans."),
    ] = False,
) -> None:
    """Run one local operator-loop pass."""

    if apply_reviewed and dry_run:
        raise typer.BadParameter("--apply-reviewed requires --no-dry-run.")
    if apply_reviewed:
        raise typer.BadParameter("--apply-reviewed needs reviewed-plan metadata; use notion apply.")
    result, event_log_path = _run_gmail_sync(dry_run=dry_run)
    _print_gmail_sync_result(result, dry_run=dry_run, event_log_path=event_log_path)


@app.command("evaluate")
def evaluate(opportunity_id: Annotated[str, typer.Argument()]) -> None:
    """Evaluate one opportunity identifier or pasted title locally."""

    settings = get_settings()
    observability = _observability()
    posting = JobPosting(
        source_url="https://example.com/manual-review",
        provider="manual",
        company="Manual Review",
        role=opportunity_id,
        description=opportunity_id,
        apply_url="https://example.com/manual-review",
    )
    result = PydanticAIService(
        model=settings.pydantic_ai_model,
        observability=observability,
    ).evaluate(posting)
    EventLog(settings.event_log_path).append(
        event_type=EventType.AI_EVALUATION_COMPLETED,
        source="manual",
        source_id=opportunity_id,
        data={
            "fit_score": result.fit_score,
            "confidence_score": result.confidence_score,
            "recommended_next_action": result.suggested_next_action,
            "prompt_version": OPPORTUNITY_EVALUATOR_PROMPT_VERSION,
        },
    )
    table = Table(title="Opportunity Evaluation")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Opportunity", opportunity_id)
    table.add_row("Fit Score", str(result.fit_score))
    table.add_row("Confidence", f"{result.confidence_score:.0f}")
    table.add_row("Next Action", result.suggested_next_action)
    table.add_row("Summary", result.executive_summary)
    console.print(table)


@app.command("events")
def events(limit: Annotated[int, typer.Option(help="Number of events to show.")] = 10) -> None:
    """Show recent workflow events."""

    event_log = EventLog(get_settings().event_log_path)
    table = Table(title="Career Forge Events")
    table.add_column("Created")
    table.add_column("Type")
    table.add_column("Source")
    table.add_column("Source ID")
    for event in event_log.tail(limit):
        table.add_row(
            event.created_at.isoformat(),
            event.event_type.value,
            event.source,
            event.source_id,
        )
    console.print(table)


@app.command()
def today() -> None:
    """Show the primary daily Career Forge action queue."""

    table = Table(title="Career Forge Today")
    table.add_column("Queue")
    table.add_column("Action")
    table.add_column("Source")
    table.add_row("Apply", "Pick 1 high-fit Ready to Apply opportunity", "Opportunities Pipeline")
    table.add_row("Follow up", "Send due follow-ups before noon", "Follow-Ups")
    table.add_row("Review", "Clear stale or needs-human-decision items", "Agent Control Panel")
    table.add_row("Interview Prep", "Refresh prep briefs for scheduled interviews", "Interviews")
    console.print(table)


@app.command()
def followups() -> None:
    """Show follow-up work queues."""

    _print_queue(
        "Follow-Ups",
        [
            ("Due Today", "Reply to recruiters or hiring teams due today."),
            ("Waiting", "Check opportunities with no response after follow-up window."),
            ("Drafts", "Review generated outreach before sending."),
        ],
    )


@app.command()
def interviews() -> None:
    """Show interview preparation queues."""

    _print_queue(
        "Interview Prep",
        [
            ("Prep Needed", "Generate or refresh company/role prep brief."),
            ("Confirmed", "Check schedule, contact, and expected format."),
            ("Post-Interview", "Send thank-you note and capture notes."),
        ],
    )


@app.command()
def recruiter() -> None:
    """Show recruiter outreach queues."""

    _print_queue(
        "Recruiter Outreach",
        [
            ("To Contact", "Draft outreach for high-priority opportunities."),
            ("Follow-Up", "Respond to recruiter follow-ups."),
            ("Relationships", "Update contact notes after conversations."),
        ],
    )


@app.command()
def pipeline() -> None:
    """Show pipeline review queues."""

    _print_queue(
        "Opportunity Pipeline",
        [
            ("Ready to Apply", "Apply or archive."),
            ("Researching", "Complete company research and fit check."),
            ("Waiting", "Monitor applications waiting on response."),
            ("Stale", "Review items with no recent activity."),
        ],
    )


@app.command()
def metrics() -> None:
    """Print weekly analytics summary."""

    analytics = generate_weekly_analytics(WeeklyAnalyticsInput(week_start=date.today()))
    table = Table(title="Weekly Metrics")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Applications Submitted", str(analytics.applications_submitted))
    table.add_row("Response Rate", f"{analytics.response_rate:.0%}")
    table.add_row("Interview Rate", f"{analytics.interview_rate:.0%}")
    table.add_row("Offer Rate", f"{analytics.offer_rate:.0%}")
    table.add_row("Recruiter Response Rate", f"{analytics.recruiter_response_rate:.0%}")
    console.print(table)


@app.command("feedback")
def feedback(
    limit: Annotated[int | None, typer.Option(help="Only analyze the latest N events.")] = None,
    emit_logfire: Annotated[
        bool,
        typer.Option(help="Emit the feedback report to Logfire as structured observations."),
    ] = False,
) -> None:
    """Summarize closed-loop Logfire/eval feedback from workflow events."""

    settings = get_settings()
    event_log = EventLog(settings.event_log_path)
    events = event_log.tail(limit) if limit is not None else event_log.read_all()
    report = build_feedback_loop_report(events)
    if emit_logfire:
        _emit_feedback_to_logfire(report)
    _print_feedback_report(report)


@app.command("evals")
def run_evals(
    emit_logfire: Annotated[
        bool,
        typer.Option(help="Emit eval summaries and metrics to Logfire."),
    ] = True,
) -> None:
    """Run prompt eval fixtures and publish summaries to Logfire."""

    settings = get_settings()
    observability = _observability() if emit_logfire else None
    summaries = LogfireEvalRunner(observability=observability).run_all()

    event_log = EventLog(settings.event_log_path)
    table = Table(title="Career Forge Evals")
    table.add_column("Dataset")
    table.add_column("Prompt")
    table.add_column("Model/Route")
    table.add_column("Cases")
    table.add_column("Passed")
    table.add_column("Failed")
    table.add_column("Pass Rate")
    for summary in summaries:
        event_log.append(
            event_type=EventType.PROMPT_EVAL_COMPLETED,
            source="evals",
            source_id=summary.dataset_name,
            data={
                "prompt_version": summary.prompt_version,
                "cases": summary.cases,
                "passed": summary.passed,
                "failed": summary.failed,
                "pass_rate": summary.pass_rate,
                "model_route": summary.model_route,
            },
        )
        event_log.append(
            event_type=EventType.EVAL_COMPLETED,
            source="evals",
            source_id=summary.dataset_name,
            data={
                "prompt_version": summary.prompt_version,
                "cases": summary.cases,
                "passed": summary.passed,
                "failed": summary.failed,
                "pass_rate": summary.pass_rate,
                "model_route": summary.model_route,
                "event_log_entries_appended": 2,
            },
        )
        table.add_row(
            summary.dataset_name,
            summary.prompt_version,
            summary.model_route,
            str(summary.cases),
            str(summary.passed),
            str(summary.failed),
            f"{summary.pass_rate:.0%}",
        )
    console.print(table)


@app.command("logfire-sync")
def logfire_sync(
    emit_logfire: Annotated[
        bool,
        typer.Option(help="Emit catalog records to Logfire."),
    ] = True,
) -> None:
    """Sync agents, prompts, LLMs, and providers into Logfire metadata."""

    observability = _observability() if emit_logfire else None
    items = emit_logfire_catalog(observability) if observability else full_catalog()
    table = Table(title="Career Forge Logfire Catalog")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("Owner")
    for item in items:
        table.add_row(item.kind, item.name, item.version, item.status, item.owner)
    console.print(table)


@app.command()
def stale() -> None:
    """Show stale pipeline items that need a decision."""

    event_log = EventLog(get_settings().event_log_path)
    rows = [
        (
            event.source_id,
            str(event.data.get("detail", "Review stale application.")),
        )
        for event in event_log.read_all()
        if event.event_type == EventType.HUMAN_REVIEW_REQUIRED
        and event.source == "application_status_guardian"
        and event.data.get("kind") == "stale_application"
    ]
    _print_queue("Stale Applications", rows or [("None", "Run application-health to refresh.")])


@app.command("application-health")
def application_health(
    applications_path: Annotated[
        Path,
        typer.Argument(
            help="JSON file containing application records from Notion or a local fixture.",
        ),
    ],
    report_date: Annotated[
        str | None,
        typer.Option(help="Report date for deterministic stale checks."),
    ] = None,
) -> None:
    """Run the Application Status Guardian daily health report."""

    settings = get_settings()
    event_log = EventLog(settings.event_log_path)
    report = build_application_status_health_report(
        load_guardian_applications(applications_path),
        report_date=date.fromisoformat(report_date) if report_date else date.today(),
        events=event_log.read_all(),
    )
    summary_event = event_log.append(
        event_type=EventType.APPLICATION_STATUS_HEALTH_REPORTED,
        source="application_status_guardian",
        source_id=report.report_date.isoformat(),
        data=guardian_event_payload(report),
        status=EventStatus.REVIEW_REQUIRED
        if report.review_required_count > 0
        else EventStatus.COMPLETED,
    )
    for finding in report.findings:
        event_log.append(
            event_type=EventType.HUMAN_REVIEW_REQUIRED,
            source="application_status_guardian",
            source_id=finding.application_id,
            data=finding_event_payload(finding),
            correlation_id=summary_event.event_id,
            status=EventStatus.REVIEW_REQUIRED,
            replay_eligible=False,
        )
    _print_application_health_report(report)


@app.command()
def review() -> None:
    """Show human review queues generated by automations."""

    event_log = EventLog(get_settings().event_log_path)
    rows = [
        (
            event.source_id,
            str(event.data.get("recommended_action", "Review before mutation.")),
        )
        for event in event_log.read_all()
        if event.event_type == EventType.HUMAN_REVIEW_REQUIRED
    ]
    _print_queue("Manual Review", rows or [("None", "No human-review events in the event log.")])


@app.command("record-outcome")
def record_outcome(
    source_id: Annotated[str, typer.Argument(help="Application, opportunity, or message id.")],
    outcome: Annotated[
        str,
        typer.Argument(help="Outcome such as applied, response, interview, offer, rejection."),
    ],
    source: Annotated[
        str,
        typer.Option(help="Source channel, e.g. LinkedIn, recruiter, gmail."),
    ] = "manual",
) -> None:
    """Record an application outcome for feedback-loop analytics."""

    EventLog(get_settings().event_log_path).append(
        event_type=EventType.APPLICATION_OUTCOME_RECORDED,
        source=source,
        source_id=source_id,
        data={"outcome": outcome, "source": source},
    )
    console.print(f"Recorded outcome '{outcome}' for {source_id}.")


@app.command("record-override")
def record_override(
    source_id: Annotated[str, typer.Argument(help="Message, opportunity, or eval case id.")],
    original: Annotated[
        str,
        typer.Argument(help="Original automated classification/recommendation."),
    ],
    corrected: Annotated[str, typer.Argument(help="Human-corrected value.")],
    prompt_version: Annotated[
        str | None,
        typer.Option(help="Prompt version that produced the output."),
    ] = None,
) -> None:
    """Record a human override decision for prompt and scoring improvement."""

    data: dict[str, object] = {"original": original, "corrected": corrected}
    if prompt_version:
        data["prompt_version"] = prompt_version
    EventLog(get_settings().event_log_path).append(
        event_type=EventType.HUMAN_OVERRIDE_RECORDED,
        source="human",
        source_id=source_id,
        data=data,
    )
    console.print(f"Recorded override for {source_id}.")


def _run_gmail_sync(*, dry_run: bool) -> tuple[GmailSyncResult, str]:
    settings = get_settings()
    observability = _observability()
    event_log = EventLog(settings.event_log_path)
    service = GmailSyncService(
        gmail_client=_gmail_client(dry_run=dry_run),
        state_store=JsonStateStore(settings.state_path),
        event_log=event_log,
        notion_executor=_notion_executor(
            dry_run=dry_run,
            event_log=event_log,
            observability=observability,
        ),
        observability=observability,
    )
    return service.sync(labels=["INBOX"]), str(settings.event_log_path)


def _notion_executor(
    *,
    dry_run: bool,
    event_log: EventLog,
    observability: Observability,
) -> NotionUpsertExecutor:
    settings = get_settings()
    return NotionUpsertExecutor(
        gateway=None if dry_run else NotionHttpGateway(settings),
        event_log=event_log,
        dry_run=dry_run,
        observability=observability,
    )


def _notion_replay_service(*, dry_run: bool) -> NotionReplayService:
    settings = get_settings()
    observability = _observability()
    event_log = EventLog(settings.event_log_path)
    return NotionReplayService(
        event_log=event_log,
        notion_executor=_notion_executor(
            dry_run=dry_run,
            event_log=event_log,
            observability=observability,
        ),
    )


def _print_setup_validation(report: SetupValidationReport) -> None:
    table = Table(title="Setup Validation")
    table.add_column("Status")
    table.add_column("Check")
    table.add_column("Detail")
    table.add_column("Env Var")
    table.add_column("Suggested Fix")
    for item in report.items:
        table.add_row(
            item.status.value,
            item.name,
            item.detail,
            item.env_var or "",
            item.suggested_fix,
        )
    console.print(table)


def _print_gmail_sync_result(
    result: GmailSyncResult,
    *,
    dry_run: bool,
    event_log_path: str,
) -> None:
    table = Table(title="Gmail Operator Loop")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Messages inspected", str(result.fetched))
    table.add_row("Classified", str(result.processed))
    table.add_row("Skipped", str(result.skipped))
    table.add_row("Failed", str(result.failed))
    table.add_row("Notion mutation plans", str(result.mutations_planned))
    table.add_row("Low confidence", str(result.low_confidence_classifications))
    table.add_row("Mutations executed", str(result.mutations_executed))
    table.add_row("Dry run", "yes" if dry_run else "no")
    table.add_row("Event log", event_log_path)
    table.add_row("Next command", "career-forge notion plan --latest")
    console.print(table)


def _print_notion_plan(event_id: str, mutation: NotionMutation, replay_eligible: bool) -> None:
    table = Table(title="Latest Notion Mutation Plan")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Event ID", event_id)
    table.add_row("Database", mutation.database)
    table.add_row("Dedupe Key", mutation.dedupe_key)
    table.add_row("Action", mutation.action)
    table.add_row("Requires Review", "yes" if mutation.requires_review else "no")
    table.add_row("Replay Eligible", "yes" if replay_eligible else "no")
    table.add_row("Properties", json.dumps(mutation.properties, sort_keys=True))
    console.print(table)


def _print_notion_apply_result(result) -> None:
    table = Table(title="Notion Apply")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Plan event", result.event.event_id)
    table.add_row("Database", result.mutation.database)
    table.add_row("Dedupe Key", result.mutation.dedupe_key)
    table.add_row("Executed", str(result.execution.executed))
    table.add_row("Dry-run records", str(result.execution.dry_run))
    table.add_row("Skipped", str(result.execution.skipped))
    table.add_row("Failed", str(result.execution.failed))
    console.print(table)


def _print_queue(title: str, rows: list[tuple[str, str]]) -> None:
    table = Table(title=title)
    table.add_column("Queue")
    table.add_column("Next Action")
    for queue, action in rows:
        table.add_row(queue, action)
    console.print(table)


def _print_application_health_report(report: ApplicationStatusHealthReport) -> None:
    summary = Table(title="Application Status Guardian")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Report date", report.report_date.isoformat())
    summary.add_row("Applications checked", str(report.applications_checked))
    summary.add_row("Stale applications", str(report.stale_count))
    summary.add_row("Missing data", str(report.missing_data_count))
    summary.add_row("Status conflicts", str(report.status_conflict_count))
    summary.add_row("Human review required", str(report.review_required_count))
    console.print(summary)

    if not report.findings:
        return

    findings = Table(title="Guardian Findings")
    findings.add_column("Kind")
    findings.add_column("Application")
    findings.add_column("Detail")
    findings.add_column("Next Action")
    for finding in report.findings:
        findings.add_row(
            finding.kind,
            finding.application_id,
            finding.detail,
            finding.recommended_action,
        )
    console.print(findings)


def _print_feedback_report(report: FeedbackLoopReport) -> None:
    metrics_table = Table(title="Career Forge Feedback Loop")
    metrics_table.add_column("Metric")
    metrics_table.add_column("Value")
    for name, value in report.metrics.items():
        metrics_table.add_row(name.replace("_", " ").title(), str(value))
    console.print(metrics_table)

    if report.alerts:
        alert_table = Table(title="Feedback Alerts")
        alert_table.add_column("Severity")
        alert_table.add_column("Alert")
        alert_table.add_column("Recommendation")
        for alert in report.alerts:
            alert_table.add_row(alert.severity, alert.name, alert.recommendation)
        console.print(alert_table)

    if report.prompt_performance:
        prompt_table = Table(title="Prompt Performance")
        prompt_table.add_column("Prompt")
        prompt_table.add_column("Samples")
        prompt_table.add_column("Avg Confidence")
        prompt_table.add_column("Low Confidence")
        prompt_table.add_column("Overrides")
        for prompt in report.prompt_performance:
            prompt_table.add_row(
                prompt.prompt_version,
                str(prompt.sample_count),
                "" if prompt.average_confidence is None else str(prompt.average_confidence),
                f"{prompt.low_confidence_rate:.0%}",
                str(prompt.override_count),
            )
        console.print(prompt_table)

    if report.source_quality:
        source_table = Table(title="Source Quality")
        source_table.add_column("Source")
        source_table.add_column("Applications")
        source_table.add_column("Response Rate")
        source_table.add_column("Interview Rate")
        source_table.add_column("Quality")
        for source in report.source_quality:
            source_table.add_row(
                source.source,
                str(source.applications),
                f"{source.response_rate:.0%}",
                f"{source.interview_conversion_rate:.0%}",
                str(source.quality_score),
            )
        console.print(source_table)

    action_table = Table(title="Improvement Actions")
    action_table.add_column("Action")
    for action in report.improvement_actions:
        action_table.add_row(action)
    console.print(action_table)


def _print_single_message_result(result: SingleMessageWriteResult) -> None:
    summary = Table(title="Single Gmail Message Control")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Message ID", result.message_id)
    summary.add_row("Mode", "dry-run" if result.dry_run else "live")
    summary.add_row("Classification", result.classification)
    summary.add_row("Confidence", f"{result.confidence:.2f}")
    summary.add_row("Human Review", "yes" if result.requires_human_review else "no")
    summary.add_row("Candidate mutations", str(len(result.mutations)))
    summary.add_row(
        "Selected mutation",
        "all previewed" if result.dry_run else str(result.selected_mutation_index),
    )
    summary.add_row("Executed", str(result.execution.executed))
    summary.add_row("Dry-run records", str(result.execution.dry_run))
    summary.add_row("Failed", str(result.execution.failed))
    console.print(summary)

    plan = Table(title="Candidate Notion Mutations")
    plan.add_column("Index")
    plan.add_column("Database")
    plan.add_column("Dedupe Key")
    plan.add_column("Action")
    plan.add_column("Properties")
    for index, mutation in enumerate(result.mutations):
        plan.add_row(
            str(index),
            mutation.database,
            mutation.dedupe_key,
            mutation.action,
            json.dumps(mutation.properties, sort_keys=True),
        )
    console.print(plan)


def _emit_feedback_to_logfire(report: FeedbackLoopReport) -> None:
    observability = _observability()
    for name, value in report.metrics.items():
        observability.info("career_ops.feedback.metric", metric=name, value=value)
    for alert in report.alerts:
        observability.error(
            "career_ops.feedback.alert",
            alert=alert.name,
            severity=alert.severity,
            detail=alert.detail,
        )


class _EmptyGmailClient:
    def fetch_since(self, checkpoint: str | None, labels: list[str]) -> list[EmailMessage]:
        return []

    def fetch_message(self, message_id: str) -> EmailMessage:
        msg = "Gmail credentials are required to fetch a specific message."
        raise RuntimeError(msg)

    def acknowledge_processed(self, message_id: str) -> None:
        return None


def _gmail_client(*, dry_run: bool) -> GmailOAuthClient | _EmptyGmailClient:
    settings = get_settings()
    if dry_run and not settings.gmail_credentials_path.exists():
        return _EmptyGmailClient()
    return GmailOAuthClient(
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
        processed_label_name=settings.gmail_processed_label,
    )


def _gmail_client_for_message() -> GmailOAuthClient:
    settings = get_settings()
    return GmailOAuthClient(
        credentials_path=settings.gmail_credentials_path,
        token_path=settings.gmail_token_path,
        processed_label_name=settings.gmail_processed_label,
    )


def _observability() -> Observability:
    observability = Observability(get_settings())
    observability.configure()
    return observability


@draft_app.command("resume")
def draft_resume(
    title: Annotated[str, typer.Option()],
    company: Annotated[str, typer.Option()],
    description: Annotated[str, typer.Option()] = "",
) -> None:
    draft = build_resume_tailoring_notes(_opportunity_from_args(title, company, description))
    console.print(draft.body)


@draft_app.command("cover-letter")
def draft_cover_letter(
    title: Annotated[str, typer.Option()],
    company: Annotated[str, typer.Option()],
    description: Annotated[str, typer.Option()] = "",
) -> None:
    draft = build_cover_letter(_opportunity_from_args(title, company, description))
    console.print(draft.body)


@draft_app.command("recruiter-dm")
def draft_recruiter_dm(
    title: Annotated[str, typer.Option()],
    company: Annotated[str, typer.Option()],
    contact_name: Annotated[str | None, typer.Option()] = None,
    description: Annotated[str, typer.Option()] = "",
) -> None:
    draft = build_recruiter_dm(_opportunity_from_args(title, company, description), contact_name)
    console.print(draft.body)


@draft_app.command("interview-prep")
def draft_interview_prep(
    title: Annotated[str, typer.Option()],
    company: Annotated[str, typer.Option()],
    description: Annotated[str, typer.Option()] = "",
) -> None:
    draft = build_interview_prep(_opportunity_from_args(title, company, description))
    console.print(draft.body)


if __name__ == "__main__":
    app()
