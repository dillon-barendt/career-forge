# Career Forge Agents

The platform is split into small agents. Agents coordinate typed pipelines; they
do not own Notion schemas directly.

## Operating Rules

- Notion is the source of truth.
- Local code can classify, recommend, and draft automatically.
- External side effects must be idempotent and auditable.
- Low-confidence classifications require human review.
- Never permanently delete job-search data; archive instead.
- Preserve `dillon.barendt.jobs@gmail.com` as the dedicated career inbox.

## Agents

| Agent | Responsibility | Current Implementation |
| --- | --- | --- |
| Intake Agent | Route incoming email, job URLs, and review items | scaffold |
| Gmail Agent | Classify Gmail messages and produce Notion write plans | `agents/gmail.py`, `gmail/sync.py`, `gmail/single_message.py` |
| Opportunity Agent | Ingest job URLs, evaluate fit, produce opportunity records | `agents/opportunity.py` |
| Resume Agent | Generate resume tailoring notes | scaffold over existing material helpers |
| Recruiter Agent | Draft outreach and follow-ups | scaffold over existing material helpers |
| Interview Agent | Generate interview prep briefs | scaffold over existing workflow helper |
| Analytics Agent | Generate weekly metrics and recommendations | `agents/analytics.py` |
| Workflow Orchestrator | Coordinate agents without coupling providers to business logic | `agents/orchestrator.py` |

## Operator Loop

Phase 8 exposes the first replayable local loop:

```bash
career-forge setup validate
career-forge ingest-gmail --dry-run
career-forge ingest-gmail-message <gmail-message-id> --dry-run
career-forge notion plan --latest
career-forge notion apply --latest --dry-run
career-forge run-once --dry-run
```

Agents may classify, recommend, and plan, but mutation apply remains an explicit
operator action. Low-confidence plans require review and broad Gmail dry-runs do
not acknowledge or checkpoint messages.

## Pydantic AI

`PydanticAIService` owns prompt-versioned structured outputs for:

- email classification
- opportunity evaluation
- fit scoring support
- next-action recommendations
- resume, cover letter, and interview prep recommendations

Prompt versions live in `prompts/phase3/`. Eval datasets live in `evals/`.

## Failure Handling

- Provider unsupported: return `needs_human_review=True`.
- Gmail confidence below threshold: send to Manual Review queue.
- Notion API unavailable: keep local mutation plan and retry later.
- Duplicate source event: skip writes using the event dedupe key.
- Missing credentials: run in dry-run/planning mode.
- Failed Notion mutations: append `notion.mutation.failed` with replay
  eligibility instead of editing old events.
