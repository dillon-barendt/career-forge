# Data Model

Notion remains the source of truth. Local models normalize data before it is
written or displayed.

## Core Notion Databases

| Database | Purpose |
| --- | --- |
| Opportunities Pipeline | Target roles and opportunity status |
| Companies | Company research and relationship hub |
| Contacts / Recruiters | Recruiters, hiring managers, referrals |
| Applications | Submitted applications and current status |
| Interviews | Interview schedule, prep, and notes |
| Follow-Ups | Due reminders and outreach tasks |
| Career Materials | Resume, cover letter, and message assets |
| Outreach Templates | Reusable recruiter and follow-up templates |
| Research Notes | Company and role research |
| Weekly Reviews | Metrics, retrospectives, and recommendations |

## Shared Local Models

| Model | Purpose |
| --- | --- |
| `EmailMessage` | Normalized Gmail message input |
| `EmailClassification` | Category, confidence, and review flag |
| `ClassifiedGmailMessage` | Operator-facing Gmail classification contract with prompt/model/fallback metadata |
| `GmailIngestionPlan` | Extracted Notion entities plus audit metadata |
| `JobPosting` | Provider-normalized job posting |
| `OpportunityEvaluation` | Fit score, confidence, reasoning, and suggestions |
| `JobIngestionResult` | Posting, evaluation, opportunity, priority, review flag |
| `WeeklyAnalyticsInput` | Weekly applications and recruiter contacts |
| `WeeklyAnalytics` | Funnel metrics and recommendations |
| `NotionMutation` | Idempotent write intent for Notion |
| `WorkflowEvent` | Append-only workflow event record with correlation id, status, replay eligibility, and redacted summary fields |
| `WebhookRoute` | Route-level project/source identifiers |
| `WebhookEnvelope` | Provider-neutral webhook receipt with payload, redacted headers, raw body hash, dedupe key, and status |
| `WebhookAck` | Typed API acknowledgement returned to webhook providers |
| `WebhookVerificationResult` | Provider verification outcome without pretending unconfigured sources are verified |
| `WebhookProcessingResult` | Internal service result with acknowledgement, duplicate flag, and duration |
| `PydanticAIEmailEvaluation` | Structured Pydantic AI email classification |
| `GmailSyncResult` | Observable Gmail sync run summary |
| `NotionExecutionResult` | Observable Notion mutation execution summary |

## Email Categories

- Recruiter Outreach
- Application Confirmation
- Interview Invitation
- Interview Confirmation
- Offer
- Rejection
- Recruiter Follow-Up
- Company Communication
- Newsletter
- Ignore

The Phase 8 operator-facing classification contract maps these legacy labels to
explicit replay categories:

- `opportunity`
- `recruiter_contact`
- `interview`
- `follow_up`
- `rejection`
- `offer`
- `newsletter`
- `irrelevant`
- `unknown`

## Dedupe Keys

- Gmail messages: `gmail:{message_id}`
- Job URLs: `job:{source_url}`
- Companies: `company:{lowercase_company_name}`
- Contacts: `contact:{email_or_name}`
- Webhook provider event IDs: `{project}:{source}:event:{event_id}`
- Webhook fallback receipts: `sha256:{hash(project, source, raw_body_hash, stable_headers)}`

These keys are the basis for future Notion upsert behavior and audit history.
Webhook receipts currently use an in-memory store for local development; durable
storage should move to SQLite/Postgres before production multi-worker use.

## Event Types

- `gmail.sync.started`
- `gmail.sync.completed`
- `gmail.message.selected`
- `gmail.message.skipped`
- `gmail.message.classified`
- `gmail.message.classification_failed`
- `gmail.message.received`
- `email.classified`
- `notion.mutation.planned`
- `notion.mutation.applied`
- `notion.mutation.failed`
- `notion.mutation.skipped`
- `notion.mutation.executed`
- `ai.evaluation.completed`
- `operator.review_required`
- `human_review.required`
- `application_status.health_reported`
- `eval.completed`
- `error.retry`
- `webhook.received`
- `webhook.duplicate`
- `webhook.failed`
- domain events for companies, contacts, opportunities, applications,
  follow-ups, and interviews

`notion.mutation.planned` events include a serialized `NotionMutation` payload
so the CLI can inspect and replay plans without mutating older events.
