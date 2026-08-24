# Changelog

All notable changes to Career Forge are tracked here.

## 0.6.0 - 2026-08-24

### Added

- Python 3.10, 3.11, and 3.12 test matrix with a dependent Python 3.12 quality
  job for Ruff, Pyright, benchmark, host mock smoke, Docker mock smoke, and
  benchmark artifact upload.
- Explicit `CAREER_FORGE_MODE=mock` and `CAREER_FORGE_MODE=real` runtime
  selection through a centralized AI service factory.
- Isolated, versioned prompt builders and typed output parsers for email and
  opportunity model calls.
- Configurable mock responses for deterministic failure and pipeline tests.

### Changed

- Mock mode is now the credential-free default for local workflows, CI, and the
  non-root Docker image; real mode validates provider credentials before model
  construction and disables implicit local fallback.
- Gmail and job-ingestion pipelines now construct their AI services through the
  configured factory when a dependency is not injected.
- The public benchmark JSON now has the exact top-level fields `n`,
  `median_ms`, `p95_ms`, `throughput_per_min`, `success_rate`, and `details`;
  detail records contain `prompt_id`, `latency_ms`, `success`, and `error`.
- Release documentation now records mock/real commands, factory and
  prompt-codec boundaries, measured benchmark values, and the secret-free CI
  contract.

### Fixed

- Gmail acknowledgements now occur only after successful downstream writes.
- Python-version-specific compatibility shims prevent imports from depending on
  APIs unavailable before Python 3.11.

## 0.5.0 - 2026-08-24

### Added

- Credential-free three-scenario agent demo, Docker image, and 34-second terminal GIF.
- First-class deterministic AI service behind shared classification and evaluation protocols.
- Reproducible 20-prompt benchmark with median, p95, throughput, success-rate, and JSON output.
- CI gates for Ruff formatting, scoped Pyright, 80% core coverage, smoke demo, benchmark artifact, and Docker.
- `career-forge setup validate` for typed local operator configuration checks
  with secret redaction and suggested fixes.
- Replayable Notion mutation inspection and dry-run apply commands:
  `career-forge notion plan --latest` and
  `career-forge notion apply --latest --dry-run`.
- `career-forge run-once --dry-run` as a minimal local scheduled-runner
  foundation.
- Phase 8 Gmail classification contract, append-only event replay metadata, and
  Notion failed-mutation replay eligibility.
- Notion schema validation for required `Dedupe Key` rich-text properties before
  live apply.
- Logfire metric registration for Gmail message outcomes, Notion mutation
  outcomes, and operator replay commands.
- Expanded email classifier eval cases and eval summary metadata.

### Changed

- Repositioned the public project as “CareerForge — AI agents that forge career data into action.”
- Pydantic AI fallback now delegates to the explicit deterministic service instead of duplicating rules.
- Removed the unused duplicate heuristic classifier from the Gmail pipeline.
- Broad Gmail dry-runs no longer acknowledge messages, advance checkpoints, or
  mark local state as processed.
- Notion planned events now include serialized mutation payloads for replay.
- Eval command output includes the model/route and appends `eval.completed`
  while preserving `prompt_eval.completed`.

### Fixed

- Malformed AI email classification output now falls back to a structured local
  classification instead of crashing the operator loop.

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
