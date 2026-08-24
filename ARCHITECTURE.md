# Architecture

CareerForge is a local Python automation platform with Notion as the system of
record and provider adapters around every external source. Its public showcase
uses the same application paths with deterministic, credential-free adapters.

```mermaid
flowchart LR
    Gmail["Gmail Inbox"] --> GmailSync["Gmail Sync Service"]
    GmailSync --> GmailAgent["Gmail Agent"]
    URL["Job URL"] --> OpportunityAgent["Opportunity Agent"]
    Hook["Webhook POST /hooks/{project}/{source}"] --> WebhookService["Webhook Ingestion Service"]
    WebhookService --> WebhookRegistry["Source Registry"]
    WebhookRegistry --> WebhookHandler["Provider Handler"]
    WebhookService --> Logfire
    GmailAgent --> AI{"AI Service Protocol"}
    OpportunityAgent --> AI
    Demo["Demo + Benchmark"] --> GmailAgent
    Demo --> OpportunityAgent
    AI --> Deterministic["Deterministic AI Service"]
    AI --> PydanticAI["Pydantic AI Service"]
    PydanticAI --> Model["Model Provider"]
    AI --> Planner["Notion Mutation Planner"]
    Events --> Replay["Operator Replay Service"]
    Replay --> Executor
    Planner --> Executor["Notion Upsert Executor"]
    Executor --> Notion["Notion Databases"]
    Executor --> Events["Append-only Event Log"]
    GmailSync --> Events
    AI --> Logfire["Logfire"]
    Notion --> CLI["career-forge CLI"]
    Notion --> Analytics["Analytics Agent"]
```

## Layers

| Layer | Purpose |
| --- | --- |
| `models/` | Shared typed contracts across agents and providers |
| `automation/` | Event-specific planners such as Gmail ingestion |
| `providers/` | External provider adapters, kept out of business logic |
| `ingestion/` | Orchestrates provider extraction and evaluation |
| `evaluation/` | Produces structured opportunity reasoning |
| `agents/` | Thin role-based coordinators |
| `api/` | FastAPI app factory and HTTP route modules |
| `application/webhooks/` | Provider-neutral webhook ingestion, registry, verification, and idempotency |
| `infrastructure/webhooks/` | Header redaction, queue placeholders, and observability helpers |
| `notion/` | Existing direct Notion API repositories |
| `providers/notion/` | Notion mutation planning, execution, and HTTP gateway |
| `gmail/` | Gmail OAuth client and checkpointed sync service |
| `events/` | Append-only JSONL workflow event log |
| `operator_loop.py` | Replay-oriented inspection and apply service for planned Notion mutations |
| `state/` | Local checkpoint and processed-source state |
| `ai/` | Shared service protocols, deterministic rules, and live Pydantic AI adapter |
| `showcase/` | Credential-free orchestration and stable demo output |
| `benchmark/` | Versioned 20-prompt correctness and latency suite |
| `analytics/` | Pure analytics functions |
| `cli.py` | Daily operator interface |

## AI Service Boundary

`EmailClassificationService` and `OpportunityEvaluationService` are the small
application-facing contracts. `PydanticAIService` handles live model calls and
observability. `DeterministicAIService` handles reproducible rules and is the
explicit fallback dependency; it does not imitate provider I/O.

This split removes hidden exception-driven demo behavior while keeping fallback
outputs compatible with the live service contract.

## Provider Boundary

Job providers implement:

```python
class JobProvider(Protocol):
    name: str
    def can_handle(self, url: str) -> bool: ...
    def extract(self, url: str, html: str) -> JobPosting: ...
```

Adding a provider should only require a new provider class and registration in
`providers/jobs/registry.py`.

## Webhook Boundary

Incoming webhooks use the domain convention:

```text
https://hooks.concordmanage.com/{project-name}/{source-name}
```

The current live route is:

```text
POST /hooks/career-forge/notion
```

Route handlers stay thin. They validate route variables, enforce the configured
body-size limit, parse JSON, and pass raw body bytes plus headers to
`WebhookIngestionService`. Source-specific behavior is selected by
`WebhookSourceRegistry`, with handler and verifier abstractions for future
sources such as Gmail, Google Calendar, GitHub, Greenhouse, Lever, Ashby,
LinkedIn, Indeed, and internal agent callbacks.

Webhook receipts currently use an in-memory `WebhookReceiptStore` for local
development. Production deployment should replace it with durable SQLite,
Postgres, or the project storage layer before running multiple workers.

## Notion Write Strategy

The mutation planner produces `NotionMutation` objects instead of blindly
writing. Each mutation includes:

- target database
- action (`upsert`)
- dedupe key
- normalized properties

The Phase 3 executor supports dry-run mode, retry events, duplicate prevention,
and a live HTTP gateway that upserts by `Dedupe Key` when Notion credentials are
configured.

Phase 8 adds a replayable operator layer:

- `career-forge notion plan --latest` reads the latest
  `notion.mutation.planned` event and prints the serialized mutation.
- `career-forge notion apply --latest --dry-run` replays the latest unapplied
  plan without writing to Notion.
- `career-forge notion apply --latest --no-dry-run --confirm` is the explicit
  live apply path.
- low-confidence mutation plans carry review metadata and are refused by replay
  unless explicitly confirmed after review.
- live apply validates that the target database has a `Dedupe Key` rich-text
  property before upserting.

Old event records remain readable because new replay fields have defaults.
