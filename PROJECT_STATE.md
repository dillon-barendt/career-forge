# Project State

## Public Showcase

CareerForge 0.6.0 implementation and host-side local verification are complete
for the credential-free deterministic demo, integrated Gmail/job pipelines,
non-root Docker definition, exact-schema 20-prompt benchmark, and Python
3.10–3.12 CI surface. These assets exercise real agent and provider boundaries
without changing the live operator loop or its dry-run safety defaults.

Version: `0.6.0`
Last updated: 2026-08-24
Status: Implementation and local host gates complete; release readiness awaits
the pull-request Actions matrix, benchmark artifact upload, and Docker
build/smoke results. Live provider validation remains manual.

## Current Phase

Phase 9 hardening implementation and local host verification complete; the
release remains pending pull-request CI and Docker evidence before Phase 10 live
validation and reviewed apply.

## Immediate Objective

Get one observable, replayable workflow running locally:

```text
email -> classification -> event log -> Notion mutation plan -> optional apply
```

## Current Architecture

Career Forge is a local Python automation platform for a software engineering job
search. Notion is the source of truth. Gmail, ATS job boards, Pydantic AI, and
Logfire are provider-backed integrations around the domain model.

```mermaid
flowchart LR
    Gmail["Gmail"] --> GmailSync["Gmail Sync"]
    GmailSync --> AI["Pydantic AI"]
    JobURL["Job URL"] --> Providers["ATS Providers"]
    Providers --> AI
    AI --> Planner["Notion Mutation Planner"]
    Planner --> Executor["Notion Executor"]
    Executor --> Notion["Notion"]
    GmailSync --> Events["Event Log"]
    Executor --> Events
    AI --> Logfire["Logfire"]
    Notion --> CLI["career-forge CLI"]
```

## Completed Milestones

- Phase 1: Career Command Center architecture and Notion schema.
- Phase 2: Automation architecture, providers, agents, CLI, analytics.
- Phase 3: Gmail to Pydantic AI to Notion production-shaped vertical slice scaffold.
- Phase 4: Repository, documentation, OSS, and developer-experience foundation.
- Phase 5: Career Forge rename and generic webhook intake foundation.
- Phase 6: Logfire workspace integration for metrics, managed variables, Gateway routing, and eval runs.
- Phase 7: Logfire catalog sync for agents, prompts, LLMs, and providers.
- Phase 8: Replayable local operator loop with typed setup validation, dry-run
  Gmail safety, append-only replay metadata, latest Notion plan/apply commands,
  schema validation, expanded eval summaries, and `run-once --dry-run`.
- Phase 9: Public AI agent showcase with an integrated three-scenario demo,
  versioned 20-prompt benchmark, Docker image, and public evidence.
- Version 0.6.0 mock-mode hardening: Python 3.10–3.12 compatibility, explicit
  mock/real factory selection, isolated prompt codecs, mock-default pipelines,
  exact benchmark fields, secret-free matrix CI configuration, and non-root
  locked Docker definition. Pull-request Actions and Docker results are not yet
  release evidence.

## Release Readiness

- Complete: implementation, host-side lint/format/type/test gates, supported
  Python suites, deterministic demo, exact-schema benchmark, and package build.
- Pending: pull-request Actions completion for all Python jobs, benchmark
  artifact upload, and Docker build/non-root smoke verification.
- No Docker or GitHub Actions gate is recorded as passed until its remote result
  is available.

## In-Progress Work

- Live validation of the Phase 8 loop against the user's Gmail, Notion, and
  Logfire workspaces.
- Gmail dry-run ingestion with OAuth configuration still manual.
- Live Gmail OAuth configuration on the target machine.
- Live Notion upsert validation against real Notion database properties.
- Logfire project/token setup for production traces.
- Reviewed-plan metadata for future unattended apply.

## Not Yet Implemented

- Hosted scheduled Gmail polling.
- Hosted Logfire alert policies.
- Gmail history-id incremental sync.
- Calendar integration.
- Autonomous email sending or autonomous job applications.
- Full provider-specific extraction for Greenhouse, Lever, Ashby, Workday,
  LinkedIn, and Indeed.
- Deep Recruiter, Resume, Interview, and Analytics agent workflows beyond
  current scaffolding/helpers.

## Outstanding Work

- Wire cron or launchd to `career-forge run-once --dry-run` after local
  credentials are validated.
- Exercise `career-forge notion apply --latest --no-dry-run --confirm` against
  one reviewed mutation in the live workspace.
- Provider-specific API extraction for Greenhouse, Lever, Ashby, and Workday.
- Calendar integration and interview scheduling support.

## Technical Debt

- Notion gateway property mapping is intentionally conservative.
- Gmail sync uses message-id checkpointing; Gmail history-id polling is a future enhancement.
- Some agent modules are thin wrappers awaiting deeper workflows.
- Resume and recruiter agents currently reuse deterministic material helpers.

## Known Limitations

- No autonomous email sending.
- No autonomous job applications.
- Live Notion writes require `Dedupe Key` properties in target databases.
- Live Pydantic AI calls require provider credentials.
- `run-once --apply-reviewed` is intentionally blocked until reviewed-plan
  metadata exists.

## Next Priorities

1. Run `career-forge setup validate` and fix any errors.
2. Configure Gmail OAuth and run `career-forge ingest-gmail --dry-run`.
3. Inspect `career-forge notion plan --latest`.
4. Validate one live Notion upsert with explicit confirmation.
5. Wire a local daily `career-forge run-once --dry-run` launchd or cron job.
