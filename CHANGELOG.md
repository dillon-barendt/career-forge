# Changelog

All notable changes to Career Forge are tracked here.

## 0.4.0 - 2026-07-08

### Added

- Structured Logfire catalog for agents, prompt templates, LLM routes, and providers.
- `career-forge logfire-sync` command to print or emit the catalog into Logfire.
- Catalog metric coverage through `career_forge.catalog.items`.
- Tests covering catalog contents, CLI exposure, and observability metric registration.

## 0.3.0 - 2026-07-08

### Added

- Logfire metrics catalog for AI requests, fallback usage, confidence, webhook volume/latency, eval cases, and eval pass rates.
- Logfire managed variables for AI Gateway enablement, local AI fallback behavior, and webhook enablement.
- FastAPI, HTTPX, OpenAI, Pydantic AI, and optional system-metrics instrumentation through the shared observability wrapper.
- Pydantic AI Gateway settings, including direct Gateway API key support and optional routing group support.
- `career-forge evals` command that wraps JSON fixtures with `pydantic_evals.Dataset`, emits Logfire eval traces, records metrics, and appends `prompt_eval.completed` events.

### Changed

- AI classifier/evaluator spans now include agent name, prompt version, model, Gateway status, confidence metrics, and fallback metrics.
- Webhook ingestion now records receipt and duration metrics.
- Eval dataset names now use `career_forge_*`.

## 0.2.0 - 2026-07-08

### Added

- Generic FastAPI webhook intake route at `/hooks/{project_name}/{source_name}`.
- First registered webhook source for `career-forge/notion`.
- Typed webhook envelopes, acknowledgements, verification results, source registry, idempotency keys, and receipt-store interface.
- Logfire webhook instrumentation and documented channel routing plan.
- Webhook tests for routing, dedupe stability, redaction, verifier status, handler failures, and fast acknowledgements.

### Changed

- Renamed project metadata, command examples, and package distribution from Career Ops / `career-ops` to Career Forge / `career-forge`.
- Renamed the installed CLI command to `career-forge`.
- Switched preferred environment variables to `CAREER_FORGE_*` while keeping `CAREER_OPS_*` compatibility aliases.
- Moved default local runtime paths to `.career_forge/`.
- Sanitized `.env.example` placeholders so example config does not contain real Notion tokens or database IDs.

## 0.1.0 - 2026-07-08

### Added

- Career Command Center Notion architecture baseline.
- Automation architecture with providers, agents, CLI, and analytics.
- Gmail to Pydantic AI to Notion vertical slice.
- Append-only event log and local sync state.
- Notion mutation planner, dry-run executor, and HTTP gateway.
- Pydantic AI prompt versions and eval datasets.
- OSS repository scaffolding, docs, examples, GitHub templates, and CI.
