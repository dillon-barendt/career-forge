# Roadmap

## Completed

### Phase 1: Career Command Center

- Notion operating system for opportunities, companies, contacts, applications,
  interviews, follow-ups, materials, research, and reviews.

### Phase 2: Automation Architecture

- provider abstractions
- agent scaffolding
- job URL ingestion
- CLI action queues
- weekly analytics
- Notion mutation planning

### Phase 3: Production-Shaped Vertical Slice

- Gmail OAuth client boundary
- checkpointed Gmail sync service
- Pydantic AI service for email and opportunity evaluation
- Logfire instrumentation wrapper
- append-only event log
- Notion upsert executor and HTTP gateway
- prompt/eval assets
- live external credential validation moved to the Phase 8/9 operator workflow

### Phase 4: Repository and OSS Foundation

- professional `career-forge` repository scaffold
- root-level Python package layout
- GitHub Actions, Dependabot, issue templates, PR template
- pre-commit, EditorConfig, Ruff, Pytest, UV
- expanded documentation, examples, ADRs, project state, and release checklist

### Phase 5: Career Forge Rename and Webhook Foundation

- package and CLI rename from Career Ops to Career Forge
- provider-neutral webhook intake route
- Notion webhook source scaffold
- compatibility aliases for older `CAREER_OPS_*` env vars

### Phase 6: Logfire Workspace Integration

- metrics and managed variables
- Pydantic AI Gateway routing settings
- eval run traces
- provider and webhook observability wiring

### Phase 7: Logfire Catalog Sync

- catalog records for agents, prompts, LLM routes, and providers
- `career-forge logfire-sync`
- catalog metric coverage

### Phase 8: Replayable Operator Loop Hardening

- `career-forge setup validate`
- non-mutating `career-forge ingest-gmail --dry-run`
- single-message Gmail inspection through `career-forge ingest-gmail-message`
- append-only event records with replay metadata
- typed Gmail classification contract and malformed-output fallback
- `career-forge notion plan --latest`
- `career-forge notion apply --latest --dry-run`
- low-confidence apply refusal for replayed plans
- Notion `Dedupe Key` schema validation before live apply
- Gmail, classification, mutation, and replay Logfire metrics
- expanded eval summaries and classifier fixtures
- `career-forge run-once --dry-run`

### Phase 9: Public AI Agent Showcase

- first-class deterministic AI service behind shared typed protocols
- three-scenario, credential-free demo through real agent pipelines
- reproducible Python 3.12 Docker image
- 20-prompt correctness and latency benchmark with JSON output
- CI gates for lint, format, scoped typing, 80% core coverage, smoke demo, benchmark, and Docker
- public-first README, terminal demo GIF, community standards, and MIT license

### Version 0.6.0: Mock-Mode Hardening

- Python 3.10–3.12 support enforced by metadata and matrix CI
- explicit mock-default and fail-fast real-provider runtime modes
- centralized AI service factory and isolated prompt-codec boundary
- Gmail and job-ingestion pipelines wired through configured AI services
- exact benchmark schema: `n`, `median_ms`, `p95_ms`,
  `throughput_per_min`, `success_rate`, and `details`
- secret-free host and non-root Docker mock smoke gates
- locked Docker dependency installation through `uv.lock`

The 0.6.0 implementation and host-side local verification are complete. Release
readiness still requires the pull-request Actions matrix, benchmark artifact
upload, and Docker build/non-root smoke gates; none of those remote gates is
recorded as passed yet.

## Recommended Phase 10: Live Validation and Reviewed Apply

1. Run the Phase 8 loop against the real dedicated Gmail inbox.
2. Validate target Notion databases include `Dedupe Key` rich-text properties.
3. Execute one reviewed live Notion apply with `--no-dry-run --confirm`.
4. Add explicit reviewed-plan metadata for future `run-once --apply-reviewed`.
5. Configure local launchd or cron for `career-forge run-once --dry-run`.
6. Add hosted Logfire alert policies for failures and confidence drift.
7. Keep broad live sync disabled until the single-message path is validated.

## Later Platform Work

- Add hosted or durable scheduling for reviewed, non-dry-run operation.
- Publish eval summaries and prompt-version metrics to Logfire.
- Add provider-specific API extraction for Greenhouse, Lever, Ashby, Workday.
- Add Gmail history-id polling for high-volume inboxes.
- Add explicit Notion review queues for failed mutations and low-confidence AI.

## Future Features

- Dream Company Watch
- Calendar integration
- recruiter relationship analytics
- provider plugins
- marketplace for custom agents
- Interview Agent
- Resume Agent
- dashboard UI
- web frontend
- API server

## Intentional Non-Goals For Now

- Fully autonomous sending of recruiter emails.
- Permanent deletion of records.
- Applying to jobs without human confirmation.
- Complex dashboard decoration outside Notion.
