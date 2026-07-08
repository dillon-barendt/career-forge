from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from career_ops.observability import Observability

CatalogKind = Literal["agent", "prompt", "llm", "provider"]


@dataclass(frozen=True)
class CatalogItem:
    kind: CatalogKind
    name: str
    version: str
    owner: str
    status: str
    description: str
    path: str | None = None
    tags: tuple[str, ...] = ()


AGENT_CATALOG: tuple[CatalogItem, ...] = (
    CatalogItem(
        kind="agent",
        name="intake",
        version="scaffold",
        owner="agents/intake.py",
        status="scaffold",
        description="Routes incoming email, job URLs, and review items.",
        path="career_ops/agents/intake.py",
        tags=("routing", "triage"),
    ),
    CatalogItem(
        kind="agent",
        name="gmail",
        version="v1",
        owner="agents/gmail.py",
        status="in_progress",
        description="Classifies Gmail messages and produces Notion write plans.",
        path="career_ops/agents/gmail.py",
        tags=("gmail", "classification", "notion"),
    ),
    CatalogItem(
        kind="agent",
        name="opportunity",
        version="v1",
        owner="agents/opportunity.py",
        status="in_progress",
        description="Ingests job URLs, evaluates fit, and produces opportunity records.",
        path="career_ops/agents/opportunity.py",
        tags=("jobs", "fit-scoring"),
    ),
    CatalogItem(
        kind="agent",
        name="resume",
        version="scaffold",
        owner="agents/resume.py",
        status="scaffold",
        description="Generates resume tailoring notes.",
        path="career_ops/agents/resume.py",
        tags=("materials", "resume"),
    ),
    CatalogItem(
        kind="agent",
        name="recruiter",
        version="scaffold",
        owner="agents/recruiter.py",
        status="scaffold",
        description="Drafts recruiter outreach and follow-ups.",
        path="career_ops/agents/recruiter.py",
        tags=("outreach", "followups"),
    ),
    CatalogItem(
        kind="agent",
        name="interview",
        version="scaffold",
        owner="agents/interview.py",
        status="scaffold",
        description="Generates interview preparation briefs.",
        path="career_ops/agents/interview.py",
        tags=("interviews", "prep"),
    ),
    CatalogItem(
        kind="agent",
        name="analytics",
        version="v1",
        owner="agents/analytics.py",
        status="in_progress",
        description="Generates weekly metrics and recommendations.",
        path="career_ops/agents/analytics.py",
        tags=("analytics", "feedback-loop"),
    ),
    CatalogItem(
        kind="agent",
        name="workflow_orchestrator",
        version="v1",
        owner="agents/orchestrator.py",
        status="in_progress",
        description="Coordinates agents without coupling providers to business logic.",
        path="career_ops/agents/orchestrator.py",
        tags=("orchestration",),
    ),
)

LLM_CATALOG: tuple[CatalogItem, ...] = (
    CatalogItem(
        kind="llm",
        name="openai:gpt-5.2",
        version="configured",
        owner="PydanticAIService",
        status="active",
        description="Default direct OpenAI model for structured Pydantic AI outputs.",
        tags=("openai", "pydantic-ai"),
    ),
    CatalogItem(
        kind="llm",
        name="gateway/openai:gpt-5.2",
        version="configured",
        owner="PydanticAIService",
        status="available",
        description="Pydantic AI Gateway route for OpenAI-compatible model calls.",
        tags=("logfire-gateway", "openai", "pydantic-ai"),
    ),
    CatalogItem(
        kind="llm",
        name="deterministic-local-fallback",
        version="v1",
        owner="PydanticAIService",
        status="active",
        description="Local deterministic fallback used for dry-runs, tests, and provider failures.",
        tags=("fallback", "offline"),
    ),
)

PROVIDER_CATALOG: tuple[CatalogItem, ...] = (
    CatalogItem(
        kind="provider",
        name="gmail",
        version="v1",
        owner="gmail/client.py",
        status="in_progress",
        description="OAuth-backed dedicated career inbox provider.",
        path="career_ops/gmail/client.py",
        tags=("email", "oauth"),
    ),
    CatalogItem(
        kind="provider",
        name="notion",
        version="v1",
        owner="providers/notion",
        status="in_progress",
        description="Workspace persistence and mutation execution provider.",
        path="career_ops/providers/notion",
        tags=("workspace", "persistence"),
    ),
    CatalogItem(
        kind="provider",
        name="logfire",
        version="v1",
        owner="observability.py",
        status="active",
        description="Traces, metrics, managed variables, evals, and Gateway observability.",
        path="career_ops/observability.py",
        tags=("observability", "evals", "gateway"),
    ),
    CatalogItem(
        kind="provider",
        name="webhooks",
        version="v1",
        owner="application/webhooks",
        status="in_progress",
        description="Generic webhook intake for Notion and future providers.",
        path="career_ops/application/webhooks",
        tags=("webhooks", "ingestion"),
    ),
    CatalogItem(
        kind="provider",
        name="ats-generic",
        version="scaffold",
        owner="providers/jobs",
        status="scaffold",
        description="Generic ATS job posting extraction provider registry.",
        path="career_ops/providers/jobs",
        tags=("jobs", "ats"),
    ),
    CatalogItem(
        kind="provider",
        name="pydantic-ai-gateway",
        version="configured",
        owner="PydanticAIService",
        status="available",
        description="Optional Pydantic AI Gateway provider for model routing and spend controls.",
        tags=("logfire-gateway", "llm-provider"),
    ),
)


def prompt_catalog(prompt_root: Path = Path("prompts")) -> tuple[CatalogItem, ...]:
    items: list[CatalogItem] = []
    if not prompt_root.exists():
        return ()
    for path in sorted(prompt_root.rglob("*.md")):
        version = path.stem
        if path.parent.name == "phase3":
            version = path.stem.replace("_", "-")
        items.append(
            CatalogItem(
                kind="prompt",
                name=path.stem.replace("_", "-"),
                version=version,
                owner=str(path),
                status="active" if path.parent.name == "phase3" else "available",
                description=f"Prompt template from {path}.",
                path=str(path),
                tags=("prompt", path.parent.name),
            )
        )
    return tuple(items)


def full_catalog(prompt_root: Path = Path("prompts")) -> tuple[CatalogItem, ...]:
    return (
        *AGENT_CATALOG,
        *prompt_catalog(prompt_root),
        *LLM_CATALOG,
        *PROVIDER_CATALOG,
    )


def emit_logfire_catalog(
    observability: Observability,
    *,
    prompt_root: Path = Path("prompts"),
) -> tuple[CatalogItem, ...]:
    items = full_catalog(prompt_root)
    for item in items:
        observability.info(
            f"career_ops.catalog.{item.kind}",
            catalog_kind=item.kind,
            name=item.name,
            version=item.version,
            owner=item.owner,
            status=item.status,
            description=item.description,
            path=item.path,
            tags=list(item.tags),
        )
        observability.increment(
            "career_forge.catalog.items",
            catalog_kind=item.kind,
            status=item.status,
        )
    return items
