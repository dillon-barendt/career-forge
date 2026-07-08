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
- live external credential validation remains part of Phase 5

### Phase 4: Repository and OSS Foundation

- professional `career-forge` repository scaffold
- root-level Python package layout
- GitHub Actions, Dependabot, issue templates, PR template
- pre-commit, EditorConfig, Ruff, Pytest, UV
- expanded documentation, examples, ADRs, project state, and release checklist

## Recommended Phase 5: Vertical Slice Hardening

1. Finish typed settings and setup validation for local credentials.
2. Run Gmail dry-run ingestion against the dedicated inbox.
3. Lock the email classification schema and confidence thresholds.
4. Verify append-only event log replay/debug behavior with real messages.
5. Validate Notion mutation planner output against the live schema.
6. Use `career-forge ingest-gmail-message` for single-message dry-run review.
7. Execute the first live Notion upsert from one selected Gmail message mutation.
8. Expand Logfire trace coverage across Gmail, classification, planning, and writes.
9. Wrap JSON eval datasets with a runnable eval harness.

## Later Platform Work

- Add a scheduled runner for `career-forge ingest-gmail --no-dry-run`.
- Add a replay command for failed Notion mutation events.
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
