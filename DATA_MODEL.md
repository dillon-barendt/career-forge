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
| `GmailIngestionPlan` | Extracted Notion entities plus audit metadata |
| `JobPosting` | Provider-normalized job posting |
| `OpportunityEvaluation` | Fit score, confidence, reasoning, and suggestions |
| `JobIngestionResult` | Posting, evaluation, opportunity, priority, review flag |
| `WeeklyAnalyticsInput` | Weekly applications and recruiter contacts |
| `WeeklyAnalytics` | Funnel metrics and recommendations |
| `NotionMutation` | Idempotent write intent for Notion |
| `WorkflowEvent` | Append-only workflow event record |
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

- `gmail.message.received`
- `email.classified`
- `notion.mutation.planned`
- `notion.mutation.executed`
- `ai.evaluation.completed`
- `human_review.required`
- `error.retry`
- `webhook.received`
- `webhook.duplicate`
- `webhook.failed`
- domain events for companies, contacts, opportunities, applications,
  follow-ups, and interviews
