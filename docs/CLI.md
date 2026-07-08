# CLI

The `career-forge` command is the daily operator interface.

## Daily

```bash
career-forge today
```

Shows the action queues: apply, follow up, review, and interview prep.

## Gmail Sync

```bash
career-forge ingest-gmail --dry-run
career-forge ingest-gmail --no-dry-run
```

Dry-run mode is the default and plans Notion mutations without live writes.

## Single-Message Gmail Control

```bash
career-forge ingest-gmail-message <gmail-message-id> --dry-run
career-forge ingest-gmail-message <gmail-message-id> \
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
career-forge ingest-url "https://jobs.lever.co/example/backend"
```

Selects a provider, extracts a normalized posting, evaluates it with Pydantic
AI, and prints fit/priority guidance.

## Notion

```bash
career-forge sync-notion --dry-run
```

Verifies Notion sync wiring. Replay of queued failed mutations is planned.

## Events

```bash
career-forge events --limit 20
```

Reads recent append-only workflow events from `.career_forge/events.jsonl`.

## Feedback Loop

```bash
career-forge feedback
career-forge feedback --emit-logfire
career-forge evals
career-forge record-outcome app_123 interview --source Recruiter
career-forge record-override msg_123 "Company Communication" "Recruiter Outreach" \
  --prompt-version email-classifier-v1
```

Summarizes classification confidence, fit scores, outcomes, source quality,
prompt performance, and alert conditions. `--emit-logfire` sends the summary to
Logfire as structured observations.

## Materials

```bash
career-forge draft resume --title "Backend Engineer" --company "Acme"
career-forge draft cover-letter --title "Backend Engineer" --company "Acme"
career-forge draft recruiter-dm --title "Backend Engineer" --company "Acme"
```
