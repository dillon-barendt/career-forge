# CLI

The `career-ops` command is the daily operator interface.

## Daily

```bash
career-ops today
```

Shows the action queues: apply, follow up, review, and interview prep.

## Gmail Sync

```bash
career-ops ingest-gmail --dry-run
career-ops ingest-gmail --no-dry-run
```

Dry-run mode is the default and plans Notion mutations without live writes.

## Single-Message Gmail Control

```bash
career-ops ingest-gmail-message <gmail-message-id> --dry-run
career-ops ingest-gmail-message <gmail-message-id> \
  --no-dry-run \
  --mutation-index 0 \
  --confirm-message-id <gmail-message-id>
```

Use this before broad live sync. Dry-run mode prints every candidate Notion
mutation with an index. Live mode applies exactly one selected mutation, requires
the same message id as confirmation, and does not advance the broad Gmail
checkpoint.

## Job URL Ingestion

```bash
career-ops ingest-url "https://jobs.lever.co/example/backend"
```

Selects a provider, extracts a normalized posting, evaluates it with Pydantic
AI, and prints fit/priority guidance.

## Notion

```bash
career-ops sync-notion --dry-run
```

Verifies Notion sync wiring. Replay of queued failed mutations is planned.

## Events

```bash
career-ops events --limit 20
```

Reads recent append-only workflow events from `.career_ops/events.jsonl`.

## Feedback Loop

```bash
career-ops feedback
career-ops feedback --emit-logfire
career-ops record-outcome app_123 interview --source Recruiter
career-ops record-override msg_123 "Company Communication" "Recruiter Outreach" \
  --prompt-version email-classifier-v1
```

Summarizes classification confidence, fit scores, outcomes, source quality,
prompt performance, and alert conditions. `--emit-logfire` sends the summary to
Logfire as structured observations.

## Materials

```bash
career-ops draft resume --title "Backend Engineer" --company "Acme"
career-ops draft cover-letter --title "Backend Engineer" --company "Acme"
career-ops draft recruiter-dm --title "Backend Engineer" --company "Acme"
```
