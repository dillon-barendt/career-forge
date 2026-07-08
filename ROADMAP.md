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

### Phase 3: Production Vertical Slice

- Gmail OAuth client boundary
- checkpointed Gmail sync service
- Pydantic AI service for email and opportunity evaluation
- Logfire instrumentation wrapper
- append-only event log
- Notion upsert executor and HTTP gateway
- prompt/eval assets

### Phase 4: Repository and OSS Foundation

- professional `career-ops` repository scaffold
- root-level Python package layout
- GitHub Actions, Dependabot, issue templates, PR template
- pre-commit, EditorConfig, Ruff, Pytest, UV
- expanded documentation, examples, ADRs, project state, and release checklist

## Recommended Phase 5

1. Add a scheduled runner for `career-ops ingest-gmail --no-dry-run`.
2. Add a replay command for failed Notion mutation events.
3. Wrap JSON eval datasets with `pydantic_evals.Dataset`.
4. Publish eval summaries and prompt-version metrics to Logfire.
5. Add provider-specific API extraction for Greenhouse, Lever, Ashby, Workday.
6. Add Gmail history-id polling for high-volume inboxes.
7. Add explicit Notion review queues for failed mutations and low-confidence AI.

## Future Features

- Interview Agent
- Resume Agent
- Dream Company Watch
- Calendar integration
- recruiter relationship analytics
- provider plugins
- marketplace for custom agents
- dashboard UI
- web frontend
- API server

## Intentional Non-Goals For Now

- Fully autonomous sending of recruiter emails.
- Permanent deletion of records.
- Applying to jobs without human confirmation.
- Complex dashboard decoration outside Notion.
