# Changelog

All notable changes to Career Forge are tracked here.

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
